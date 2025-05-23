import networkx as nx
import math
from collections import deque

def is_real_node(G, node):
    """Verifica se un nodo è reale (non added)"""
    return G.nodes[node].get('type') != 'added'

def get_real_nodes(G):
    """Restituisce tutti i nodi reali del grafo"""
    return [node for node in G.nodes() if is_real_node(G, node)]

# ------------------------------------------------------------------
# CACHING -----------------------------------------------------------
# ------------------------------------------------------------------
def _ensure_neighbor_cache(G):
    """
    Costruisce (una sola volta) e salva in G.graph['_real_neighbor_cache']
    la lista dei vicini reali raggiungibili via-nodi-'added' per OGNI nodo reale.
    """
    if '_real_neighbor_cache' in G.graph:
        return G.graph['_real_neighbor_cache']

    cache = {}
    real_nodes = [n for n in G.nodes if G.nodes[n].get('type') != 'added']
    for src in real_nodes:
        reached = set()
        visited = {src}
        q = deque([src])
        while q:
            cur = q.popleft()
            for nbr in G.neighbors(cur):
                if nbr in visited:
                    continue
                visited.add(nbr)
                if G.nodes[nbr].get('type') != 'added':
                    reached.add(nbr)
                else:
                    q.append(nbr)
        reached.discard(src)
        cache[src] = list(reached)
    G.graph['_real_neighbor_cache'] = cache
    return cache

def get_real_neighbors_via_added(G, node):
    """Versione cache-aware (BFS eseguito una sola volta per grafo)."""
    cache = _ensure_neighbor_cache(G)
    return cache.get(node, [])


def calculate_angle(pos1, pos2):
    """Calcola l'angolo tra due punti in gradi"""
    dx = pos2[0] - pos1[0]
    dy = pos2[1] - pos1[1]
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return 0.0
    angle_rad = math.atan2(dy, dx)
    return math.degrees(angle_rad) % 360

def _orientation(p, q, r):
    """Restituisce il prodotto vettoriale orientato: >0 antiorario, <0 orario."""
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

def _orientation_is_consistent(G_A, G_B, mapping):
    """Controlla che il segno del prodotto vettoriale tra triplette di nodi mappati sia consistente."""
    for nodeA, nodeB in mapping.items():
        neighborsA = get_real_neighbors_via_added(G_A, nodeA)
        for i in range(len(neighborsA)):
            for j in range(i+1, len(neighborsA)):
                a1, a2 = neighborsA[i], neighborsA[j]
                if a1 not in mapping or a2 not in mapping:
                    continue
                b1 = mapping[a1]
                b2 = mapping[a2]
                try:
                    orientA = _orientation(G_A.nodes[nodeA]["pos"],
                                           G_A.nodes[a1]["pos"],
                                           G_A.nodes[a2]["pos"])
                    orientB = _orientation(G_B.nodes[nodeB]["pos"],
                                           G_B.nodes[b1]["pos"],
                                           G_B.nodes[b2]["pos"])
                except KeyError:
                    continue
                if abs(orientA) < 1e-6 or abs(orientB) < 1e-6:
                    continue
                if orientA * orientB < 0:
                    return False
    return True

# ------------------------------------------------------------------
# FILTRI E HEURISTICHE ---------------------------------------------
# ------------------------------------------------------------------
def _build_candidate_map(G_A, G_B, nodes_A, nodes_B):
    """Per ogni nodo di A restituisce la lista dei nodi B compatibili."""
    # Pre-compute grado reale (più economico dei degree() classici)
    degA = {n: len(get_real_neighbors_via_added(G_A, n)) for n in nodes_A}
    degB = {n: len(get_real_neighbors_via_added(G_B, n)) for n in nodes_B}

    cand = {}
    for nA in nodes_A:
        cand[nA] = [nB for nB in nodes_B
                    if (G_A.nodes[nA]['type'] == G_B.nodes[nB]['type'] and
                        degA[nA]          == degB[nB])]
    return cand

def _partial_edge_check(G_A, G_B, mapping, nodeA, nodeB, angle_tol):
    """Controlla coerenza delle connessioni già mappate."""
    for nA_neigh in get_real_neighbors_via_added(G_A, nodeA):
        if nA_neigh not in mapping:
            continue
        nB_neigh = mapping[nA_neigh]

        # esistenza percorso
        if nB_neigh not in get_real_neighbors_via_added(G_B, nodeB):
            return False

        # angolo
        angA = angle_along_path(G_A, nodeA, nA_neigh)
        angB = angle_along_path(G_B, nodeB, nB_neigh)
        if not is_angle_similar(angA, angB, angle_tol):
            return False
    return True



def is_angle_similar(angleA, angleB, tolerance_degrees=30):
    """Verifica se due angoli sono simili entro una tolleranza"""
    if angleA is None or angleB is None:
        return False
    try:
        diff = abs(angleA - angleB)
        angular_distance = min(diff, 360.0 - diff)
        return angular_distance <= tolerance_degrees
    except (ValueError, TypeError):
        return False

def find_path_via_added(G, source, target):
    """Trova percorso minimo via nodi added."""
    # BFS che evita di passare per real nodes diversi da source e target
    visited = {source}
    queue = deque([[source]])
    while queue:
        path = queue.popleft()
        node = path[-1]
        if node == target:
            return path
        for nbr in G.neighbors(node):
            if nbr in visited:
                continue
            # consentiamo real only se è il target
            if is_real_node(G, nbr) and nbr != target:
                continue
            visited.add(nbr)
            queue.append(path + [nbr])
    return None


def angle_along_path(G, source, target):
    """Calcola angolo iniziale lungo il percorso."""
    path = None
    if G.has_edge(source, target):
        # percorso diretto
        return calculate_angle(G.nodes[source]['pos'], G.nodes[target]['pos'])
    # altrimenti cerca percorso via added
    path = find_path_via_added(G, source, target)
    if path and len(path) >= 2:
        next_node = path[1]
        return calculate_angle(G.nodes[source]['pos'], G.nodes[next_node]['pos'])
    return None

def is_direct_edge(G, n1, n2):
    """True se tra n1 e n2 c'è un arco non added."""
    return G.has_edge(n1, n2) and G.edges[n1, n2].get("type") != "added"


def check_edge_compatibility(G_A, G_B, mapping, angle_tolerance=30):
    """Verifica compatibilità delle connessioni tra nodi mappati."""
    for nodeA, nodeB in mapping.items():
        neighborsA = get_real_neighbors_via_added(G_A, nodeA)
        neighborsB = get_real_neighbors_via_added(G_B, nodeB)
        for nA in neighborsA:
            if nA in mapping:
                nB = mapping[nA]
                # 1) esistenza del percorso
                if nB not in neighborsB:
                    return False
                # 2) verifica angolo lungo i percorsi
                angA = angle_along_path(G_A, nodeA, nA)
                angB = angle_along_path(G_B, nodeB, nB)
                if not is_angle_similar(angA, angB, tolerance_degrees=angle_tolerance):
                    return False
    return True

def check_node_compatibility(G_A, G_B, nodeA, nodeB):
    """Verifica se due nodi hanno lo stesso tipo"""
    if not is_real_node(G_A, nodeA) or not is_real_node(G_B, nodeB):
        return False
    typeA = G_A.nodes[nodeA].get('type')
    typeB = G_B.nodes[nodeB].get('type')
    return typeA == typeB

def compute_complete_matching_score(G_A, G_B, mapping, M1_A, M1_B, M_scavalcamenti_A, M_scavalcamenti_B, 
                                   cost_weight=1.0, ridge_weight=1.0, angle_weight=1.0, edge_mode_weight=1.0):
    """Calcola score complessivo del match."""
    nodes_A = list(mapping.keys())
    total_pairs = 0
    total_score = 0
    pair_details = {}

    sum_weights = cost_weight + ridge_weight + angle_weight + edge_mode_weight
    cost_w   = cost_weight        / sum_weights
    ridge_w  = ridge_weight       / sum_weights
    angle_w  = angle_weight       / sum_weights
    edge_w   = edge_mode_weight   / sum_weights

    for i in range(len(nodes_A)):
        nodeA1 = nodes_A[i]
        nodeB1 = mapping[nodeA1]

        for j in range(i+1, len(nodes_A)):
            nodeA2 = nodes_A[j]
            nodeB2 = mapping[nodeA2]

            pair_id = (nodeA1, nodeA2)
            pair_details[pair_id] = {}

            # 1. Score per gli scavalcamenti
            try:
                scA = float(M_scavalcamenti_A[nodeA1][nodeA2])
                scB = float(M_scavalcamenti_B[nodeB1][nodeB2])
                if scA == float('inf') and scB == float('inf'):
                    sc_score = 1.0
                elif scA == float('inf') or scB == float('inf'):
                    sc_score = 0.0
                else:
                    max_sc = max(1, max(scA, scB))
                    sc_diff = abs(scA - scB)
                    sc_score = max(0.0, 1.0 - (sc_diff / max_sc))
                pair_details[pair_id]['ridge_score'] = sc_score
                pair_details[pair_id]['ridge_A'] = scA
                pair_details[pair_id]['ridge_B'] = scB
            except (IndexError, TypeError, ValueError):
                sc_score = 0.5
                pair_details[pair_id]['ridge_score'] = sc_score
                pair_details[pair_id]['error'] = "ridge_calc_error"

            # 2. Score per i costi di percorso
            try:
                costA = float(M1_A[nodeA1][nodeA2])
                costB = float(M1_B[nodeB1][nodeB2])
                if costA == float('inf') and costB == float('inf'):
                    cost_score = 1.0
                elif costA == float('inf') or costB == float('inf'):
                    cost_score = 0.0
                else:
                    max_cost = max(0.0001, max(costA, costB))
                    cost_diff = abs(costA - costB)
                    cost_score = max(0.0, 1.0 - (cost_diff / max_cost))
                pair_details[pair_id]['cost_score'] = cost_score
                pair_details[pair_id]['cost_A'] = costA
                pair_details[pair_id]['cost_B'] = costB
            except (IndexError, TypeError, ValueError):
                cost_score = 0.5
                pair_details[pair_id]['cost_score'] = cost_score
                pair_details[pair_id]['error'] = "cost_calc_error"

            # 3. Score per gli angoli
            try:
                posA1 = G_A.nodes[nodeA1]['pos']
                posA2 = G_A.nodes[nodeA2]['pos']
                posB1 = G_B.nodes[nodeB1]['pos']
                posB2 = G_B.nodes[nodeB2]['pos']
                angA = calculate_angle(posA1, posA2)
                angB = calculate_angle(posB1, posB2)
                ang_diff = min(abs(angA - angB), 360.0 - abs(angA - angB))
                angle_score = max(0.0, 1.0 - (ang_diff / 180.0))
                pair_details[pair_id]['angle_score'] = angle_score
                pair_details[pair_id]['angle_A'] = angA
                pair_details[pair_id]['angle_B'] = angB
                pair_details[pair_id]['angle_diff'] = ang_diff
            except (KeyError, TypeError, ValueError):
                angle_score = 0.5
                pair_details[pair_id]['angle_score'] = angle_score
                pair_details[pair_id]['error'] = "angle_calc_error"

            # 4. Penalità collegamento diretto vs via added
            directA = is_direct_edge(G_A, nodeA1, nodeA2)
            directB = is_direct_edge(G_B, nodeB1, nodeB2)
            if directA == directB:
                edge_mode_score = 0.4  # contribuisce 0 se la modalità è coerente (nessun premio)
            else:
                edge_mode_score = -0.01  # penalità piena in caso di mismatch
            pair_details[pair_id]['edge_mode_score'] = edge_mode_score

            pair_score = (
                ridge_w * sc_score +
                cost_w * cost_score +
                angle_w * angle_score +
                edge_w * edge_mode_score
            )
            pair_details[pair_id]['total_score'] = pair_score

            total_score += pair_score
            total_pairs += 1

    final_score = total_score / total_pairs if total_pairs > 0 else 0
    return final_score, pair_details


def match_subgraph(G_A, G_B, M1_A, M1_B, M_scavalcamenti_A, M_scavalcamenti_B, 
                  cost_threshold_rel=0.5, max_ridge_diff=1, angle_tolerance_degrees=30):
    """Verifica se due sottografi sono match compatibili."""
   
    # ----------  PRE-FILTRI RAPIDI  --------------------------------
    real_nodes_A = get_real_nodes(G_A)
    real_nodes_B = get_real_nodes(G_B)
    if len(real_nodes_A) != len(real_nodes_B):
        return False, {}, 0.0, {}

    # 1) multiset tipi
    if sorted(G_A.nodes[n]['type'] for n in real_nodes_A) != \
       sorted(G_B.nodes[n]['type'] for n in real_nodes_B):
        return False, {}, 0.0, {}

    # 2) multiset gradi reali
    degA = sorted(len(get_real_neighbors_via_added(G_A, n)) for n in real_nodes_A)
    degB = sorted(len(get_real_neighbors_via_added(G_B, n)) for n in real_nodes_B)
    if degA != degB:
        return False, {}, 0.0, {}

    
    # Prova tutte le permutazioni possibili di mapping
    best_mapping = None
    best_score = -1
    best_details = {}

        # ----------  CANDIDATE MAP + BACKTRACK  ------------------------
    cand_map = _build_candidate_map(G_A, G_B, real_nodes_A, real_nodes_B)
    # Se qualche nodo non ha candidati, match impossibile
    if any(len(v) == 0 for v in cand_map.values()):
        return False, {}, 0.0, {}

    # Ordina i nodi A per branching factor minimo (MRV)
    ordered_A = sorted(real_nodes_A, key=lambda n: len(cand_map[n]))

    best_mapping = None  # ci basta il primo valido
    def backtrack(idx, mapping, usedB):
        nonlocal best_mapping
        if idx == len(ordered_A):
            best_mapping = mapping.copy()
            return True

        nodeA = ordered_A[idx]
        for nodeB in cand_map[nodeA]:
            if nodeB in usedB:
                continue
            # pruning parziale sugli archi già fissati
            if not _partial_edge_check(G_A, G_B, mapping, nodeA, nodeB,
                                       angle_tolerance_degrees):
                continue
            mapping[nodeA] = nodeB
            usedB.add(nodeB)
            if backtrack(idx + 1, mapping, usedB):
                return True
            usedB.remove(nodeB)
            del mapping[nodeA]
        return False
    # Avvia il processo di mapping --------------------------------------
    found = backtrack(0, {}, set())
    if not found:
        return False, {}, 0.0, {}
    mapping = best_mapping
    success = True          #  <<<  AGGIUNGI questa riga


    if success:
        if not _orientation_is_consistent(G_A, G_B, mapping):
            return False, {}, 0.0, {}  # match specchiato, lo scartiamo
    score, details = compute_complete_matching_score(
        G_A, G_B, mapping, M1_A, M1_B, M_scavalcamenti_A, M_scavalcamenti_B
    )
    return success, mapping, score, details

    # else:
    #     return False, {}, 0.0, {}
