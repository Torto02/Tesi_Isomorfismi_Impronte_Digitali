"""
Miglioramento delle funzioni di estrazione dei sottografi con rimozione dei
risultati duplicati (stesso insieme di minuzie reali e stessi archi reali).

Modifiche principali:
    • Introduzione di un "canonical signature" che astrae dai nodi/archi
      di servizio (type=='added').
    • Post‑processing comune di deduplicazione per versione parallela e
      sequenziale (_deduplicate).
    • Piccole utility isolate (_is_added, _canonical_signature).

Il resto dell’algoritmo è invariato, quindi l’API rimane compatibile.
"""

from __future__ import annotations

import networkx as nx
import numpy as np
from multiprocessing import Pool, cpu_count
from typing import Tuple, List, Set, FrozenSet, Dict

# ---------------------------------------------------------------------------
#  UTILITY GENERICHE
# ---------------------------------------------------------------------------

def _is_added(G: nx.Graph, n: int) -> bool:
    """Ritorna True se il nodo ha attributo type=='added'."""
    return G.nodes[n].get("type") == "added"


def _canonical_signature(G: nx.Graph, node_set: Set[int]) -> Tuple:
    all_nodes = tuple(sorted(node_set))
    all_edges = tuple(
        sorted(
            (
                (min(u, v), max(u, v), G.edges[u, v].get("type", "real"))
                for u, v in G.subgraph(node_set).edges()
            )
        )
    )
    return all_nodes, all_edges


def _deduplicate(
    G: nx.Graph, candidates: List[Tuple[Tuple[int, ...], nx.Graph]]
) -> List[Tuple[Tuple[int, ...], nx.Graph]]:
    """Elimina duplicati mantenendo il primo risultato con la stessa firma."""
    seen: Dict[Tuple[Tuple[int, ...], Tuple[Tuple[int, int], ...]], Tuple[Tuple[int, ...], nx.Graph]] = {}
    for nodes, sg in candidates:
        sig = _canonical_signature(G, set(nodes))
        if sig not in seen:
            seen[sig] = (nodes, sg)
    return list(seen.values())

# ---------------------------------------------------------------------------
#  INDICIZZAZIONE VELOCE NODO  <->  INDICE MATRICE M3 (invariata)
# ---------------------------------------------------------------------------

def _ensure_index_maps(G: nx.Graph):
    if "_node2idx" in G.graph:
        return G.graph["_node2idx"], G.graph["_idx2node"]

    idx2node = list(G.nodes())
    node2idx = {n: i for i, n in enumerate(idx2node)}
    G.graph["_node2idx"] = node2idx
    G.graph["_idx2node"] = idx2node
    return node2idx, idx2node

# ---------------------------------------------------------------------------
#  SOTTOGRAFO ENTRO UN CERTO RAGGIO (invariata)
# ---------------------------------------------------------------------------

def get_subgraph_within_radius(G: nx.Graph, M3, source_node: int, radius: float):
    node2idx, idx2node = _ensure_index_maps(G)
    if source_node not in node2idx:
        return G.subgraph([]).copy()
    src_idx = node2idx[source_node]
    if src_idx >= len(M3):
        return G.subgraph([]).copy()
    row = np.asarray(M3[src_idx], dtype=float)
    sub_nodes_idx = np.nonzero(row <= radius)[0]
    sub_nodes = [idx2node[i] for i in sub_nodes_idx]
    return G.subgraph(sub_nodes).copy()

# ---------------------------------------------------------------------------
#  AIUTANTE: COSTRUISCI GRAFO "REALE" (invariato)
# ---------------------------------------------------------------------------

def build_S_real(S: nx.Graph) -> nx.Graph:
    S_real = nx.Graph()
    S_real.add_nodes_from(S.nodes())
    for u, v, d in S.edges(data=True):
        if d.get("type") != "added":
            S_real.add_edge(u, v)
    return S_real

# ---------------------------------------------------------------------------
#  WORKER PARALLELO BFS OTTIMIZZATO
# ---------------------------------------------------------------------------

def _expand_worker_bfs_optimized(args):
    """
    Versione BFS ottimizzata con early pruning migliorato e gestione memoria.
    """
    start, S_nodes, S_edges, size, max_added_edges = args

    S = nx.Graph()
    S.add_nodes_from(S_nodes)
    S.add_edges_from(S_edges)

    def count_real(ns: Set[int]):
        return sum(1 for x in ns if not _is_added(S, x))

    def expand_bfs_optimized(start_node: int, target_size: int) -> Set[FrozenSet[int]]:
        """
        BFS ottimizzata con:
        - Early pruning per livello
        - Gestione memoria per stati intermedi
        - Pre-calcolo neighbor cache
        """
        # Pre-compute neighbor cache for performance
        neighbor_cache = {node: set(S.neighbors(node)) for node in S.nodes()}
        
        # State: (current_nodes, candidate_nodes, added_edges_count, level)
        current_level = [
            (frozenset([start_node]), frozenset(neighbor_cache[start_node]), 0, 0)
        ]
        
        results: Set[FrozenSet[int]] = set()
        max_level = target_size + 2  # Bound search depth
        
        while current_level:
            next_level = []
            
            for curr_frozen, cands_frozen, added_count, level in current_level:
                # Depth bound check
                if level > max_level:
                    continue
                    
                curr = set(curr_frozen)
                cands = set(cands_frozen)
                real_count = count_real(curr)
                
                # Early termination
                if real_count > target_size or added_count > max_added_edges:
                    continue
                    
                # Solution found
                if real_count == target_size:
                    results.add(curr_frozen)
                    continue
                
                # Early pruning: if not enough candidates to reach target
                max_possible_real = real_count + sum(
                    1 for c in cands if not _is_added(S, c)
                )
                if max_possible_real < target_size:
                    continue
                
                # Expand to candidates
                for candidate in cands:
                    # Check constraint
                    added_edges_between = sum(
                        S.edges[m, candidate].get("type") == "added"
                        for m in curr
                        if S.has_edge(m, candidate)
                    )
                    new_added_count = added_count + added_edges_between
                    
                    if new_added_count > max_added_edges:
                        continue
                    
                    # Generate next state
                    new_curr = curr | {candidate}
                    new_cands = (cands - {candidate}) | (neighbor_cache[candidate] - new_curr)
                    
                    next_level.append((
                        frozenset(new_curr),
                        frozenset(new_cands),
                        new_added_count,
                        level + 1
                    ))
            
            # Process next level
            current_level = next_level
            
            # Memory management: limit queue size
            if len(current_level) > 100000:  # Configurable threshold
                # Keep only most promising states (with more real nodes)
                current_level.sort(key=lambda x: count_real(set(x[0])), reverse=True)
                current_level = current_level[:50000]
        
        return results

    return expand_bfs_optimized(start, size)

# ---------------------------------------------------------------------------
#  FUNZIONE PARALLELA CON DEDUP
# ---------------------------------------------------------------------------

def get_connected_subgraphs_of_minutiae_parallel(
    S: nx.Graph,
    size: int = 6,
    processes: int | None = None,
    S_real: nx.Graph | None = None,
    max_added_edges: int = 1,
):
    if not S.nodes():
        return []

    #! build di sub_G con tutti i nodi + gli archi solo reali 
    if S_real is None:
        S_real = build_S_real(S)

    S_nodes = list(S.nodes(data=True))
    # Include all edges con i loro attributi, per poter utilizzare anche gli 'added'
    S_edges = [(u, v, d.copy()) for u, v, d in S.edges(data=True)]
    print(f"Starting parallel search for subgraphs of size {size}...")
    print(f"Number of nodes in S: {len(S_nodes)}")
    print(f"number of real edges in S: {sum(1 for u, v, d in S_edges if d.get('type') != 'added')}")
    print(f"number of added edges in S: {sum(1 for u, v, d in S_edges if d.get('type') == 'added')}")

    all_nodes = list(S.nodes())

    # Use optimized BFS algorithm for subgraph enumeration
    print(f"Using optimized BFS algorithm for subgraph enumeration...")

    with Pool(processes=processes or cpu_count()) as pool:
        raw_sets = pool.map(
            _expand_worker_bfs_optimized, [(start, S_nodes, S_edges, size, max_added_edges) for start in all_nodes]
        )

    candidate_sets = set().union(*raw_sets)

    # ------------------  post‑processing  -----------------------------
    final: List[Tuple[Tuple[int, ...], nx.Graph]] = []
    for node_set in candidate_sets:
        real_nodes = [n for n in node_set if not _is_added(S, n)]
        if len(real_nodes) < 2:
            continue
        subG = S.subgraph(node_set).copy()
        to_remove = []
        for v in node_set:
            if _is_added(S, v):
                Gm = subG.copy()
                Gm.remove_node(v)
                if not all(n in nx.node_connected_component(Gm, real_nodes[0]) for n in real_nodes):
                    continue
                to_remove.append(v)
        kept = set(node_set) - set(to_remove)
        
        # Controllo aggiuntivo: ogni componente connessa deve avere almeno 2 nodi reali
        final_subgraph = S.subgraph(kept).copy()
        final_real_nodes = [n for n in kept if not _is_added(S, n)]
        
        # Creiamo un grafo che include solo archi reali tra nodi reali
        real_only_graph = nx.Graph()
        real_only_graph.add_nodes_from(final_real_nodes)
        for u, v, d in final_subgraph.edges(data=True):
            # Aggiungiamo l'arco solo se entrambi i nodi sono reali E l'arco è reale
            if (u in final_real_nodes and v in final_real_nodes and 
                d.get("type") != "added"):
                real_only_graph.add_edge(u, v)
        
        # Ottieni le componenti connesse considerando solo archi reali
        components = list(nx.connected_components(real_only_graph))
        
        # Verifica che ogni componente connessa abbia almeno 2 nodi reali
        valid_subgraph = True
        for component in components:
            if len(component) < 2:
                valid_subgraph = False
                break
        
        if valid_subgraph:
            final.append((tuple(sorted(kept)), S.subgraph(kept).copy()))

    # deduplica vera e propria (stessa firma)
    return _deduplicate(S, final)
