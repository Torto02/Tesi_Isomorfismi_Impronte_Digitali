
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


def _canonical_signature(
    G: nx.Graph, node_set: Set[int]
) -> Tuple[Tuple[int, ...], Tuple[Tuple[int, int], ...]]:
    """Restituisce una firma hashable che ignora nodi/archi 'added'."""
    real_nodes: Tuple[int, ...] = tuple(sorted(n for n in node_set if not _is_added(G, n)))

    real_edges: Tuple[Tuple[int, int], ...] = tuple(
        sorted(
            (
                (u, v) if u < v else (v, u)
                for u, v, d in G.subgraph(node_set).edges(data=True)
                if d.get("type") != "added" and not _is_added(G, u) and not _is_added(G, v)
            )
        )
    )

    return real_nodes, real_edges


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
#  WORKER PARALLELO (invariato salvo pulizia minima)
# ---------------------------------------------------------------------------

def _expand_worker(args):
    start, S_nodes, S_edges, size = args

    S = nx.Graph()
    S.add_nodes_from(S_nodes)
    S.add_edges_from(S_edges)

    def count_real(ns: Set[int]):
        return sum(1 for x in ns if not _is_added(S, x))

    results: Set[FrozenSet[int]] = set()

    def expand(curr: Set[int], cands: Set[int]):
        r = count_real(curr)
        if r == size:
            results.add(frozenset(curr))
            return
        if r > size or not cands:
            return
        for n in list(cands):
            if not _is_added(S, n) and r + 1 > size:
                continue
            new_curr = curr | {n}
            rem = cands - {n}
            new_nei = set(S.neighbors(n))
            expand(new_curr, rem | (new_nei - new_curr))

    expand({start}, set(S.neighbors(start)))
    return results

# ---------------------------------------------------------------------------
#  FUNZIONE PARALLELA CON DEDUP
# ---------------------------------------------------------------------------

def get_connected_subgraphs_of_minutiae_parallel(
    S: nx.Graph,
    size: int = 6,
    processes: int | None = None,
    S_real: nx.Graph | None = None,
):
    if not S.nodes():
        return []

    if S_real is None:
        S_real = build_S_real(S)

    S_nodes = list(S.nodes(data=True))
    S_edges = [(u, v) for u, v, d in S.edges(data=True) if d.get("type") != "added"]
    all_nodes = list(S.nodes())

    with Pool(processes=processes or cpu_count()) as pool:
        raw_sets = pool.map(
            _expand_worker, [(start, S_nodes, S_edges, size) for start in all_nodes]
        )

    candidate_sets = set().union(*raw_sets)

    # ------------------  post‑processing  -----------------------------
    final: List[Tuple[Tuple[int, ...], nx.Graph]] = []
    for node_set in candidate_sets:
        subG = S.subgraph(node_set).copy()
        real_nodes = [n for n in node_set if not _is_added(S, n)]
        to_remove = []
        if len(real_nodes) >= 2:
            for v in list(node_set):
                if _is_added(S, v):
                    Gm = subG.copy()
                    Gm.remove_node(v)
                    reachable = nx.node_connected_component(Gm, real_nodes[0])
                    if set(real_nodes).issubset(reachable):
                        to_remove.append(v)
        kept = set(node_set) - set(to_remove)
        if sum(1 for n in kept if not _is_added(S, n)) == size:
            final.append((tuple(sorted(kept)), S.subgraph(kept).copy()))

    # deduplica vera e propria (stessa firma)
    return _deduplicate(S, final)

# ---------------------------------------------------------------------------
#  FUNZIONE SEQUENZIALE CON DEDUP (stessa logica)
# ---------------------------------------------------------------------------

def get_connected_subgraphs_of_minutiae(S: nx.Graph, size: int = 6):
    if not S.nodes():
        return []

    S_real = build_S_real(S)

    risultati_sets: Set[FrozenSet[int]] = set()

    def count_real(ns: Set[int]):
        return sum(1 for x in ns if not _is_added(S, x))

    def expand(curr: Set[int], cands: Set[int]):
        r = count_real(curr)
        if r == size:
            risultati_sets.add(frozenset(curr))
            return
        if r > size or not cands:
            return
        for n in list(cands):
            if not _is_added(S, n) and r + 1 > size:
                continue
            new_curr = curr | {n}
            rem = cands - {n}
            new_nei = set(S_real.neighbors(n))
            expand(new_curr, rem | (new_nei - new_curr))

    for start in S.nodes():
        expand({start}, set(S_real.neighbors(start)))

    final: List[Tuple[Tuple[int, ...], nx.Graph]] = []
    for node_set in risultati_sets:
        subG = S.subgraph(node_set).copy()
        real_nodes = [n for n in node_set if not _is_added(S, n)]
        to_remove = []
        if len(real_nodes) >= 2:
            for v in list(node_set):
                if _is_added(S, v):
                    Gm = subG.copy()
                    Gm.remove_node(v)
                    reachable = nx.node_connected_component(Gm, real_nodes[0])
                    if set(real_nodes).issubset(reachable):
                        to_remove.append(v)
        kept = set(node_set) - set(to_remove)
        if sum(1 for n in kept if not _is_added(S, n)) == size:
            final.append((tuple(sorted(kept)), S.subgraph(kept).copy()))

    return _deduplicate(S, final)
