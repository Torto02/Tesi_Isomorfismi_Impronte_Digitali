import networkx as nx
import math
from collections import deque

def is_real_node(G, node):
    """Verifica se un nodo è reale (non added)"""
    return G.nodes[node].get('type') != 'added'

def get_real_nodes(G):
    """Restituisce tutti i nodi reali del grafo"""
    return [node for node in G.nodes() if is_real_node(G, node)]

def get_real_neighbors_via_added(G, node):
    """
    Ritorna tutti i nodi reali di G connessi a 'node' attraverso
    un percorso che attraversa solo nodi 'added' come intermedi.
    Include anche i vicini reali diretti.
    """
    real_neighbors = []
    for target in G.nodes():
        if target == node or not is_real_node(G, target):
            continue
        # Caso 1: adiacenza diretta
        if G.has_edge(node, target):
            real_neighbors.append(target)
            continue
        # Caso 2: cerca un percorso tramite soli added
        visited = {node}
        queue = deque([node])
        found = False
        while queue and not found:
            cur = queue.popleft()
            for nbr in G.neighbors(cur):
                if nbr == target and is_real_node(G, nbr):
                    real_neighbors.append(target)
                    found = True
                    break
                if nbr not in visited and not is_real_node(G, nbr):
                    visited.add(nbr)
                    queue.append(nbr)
            
    return real_neighbors


def calculate_angle(pos1, pos2):
    """Calcola l'angolo tra due punti in gradi"""
    dx = pos2[0] - pos1[0]
    dy = pos2[1] - pos1[1]
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return 0.0
    angle_rad = math.atan2(dy, dx)
    return math.degrees(angle_rad) % 360


def is_angle_similar(angleA, angleB, tolerance_degrees=30):
    """Verifica se due angoli sono simili entro una tolleranza"""
    if angleA is None or angleB is None:
        return False
    diff = abs(angleA - angleB)
    angular_distance = min(diff, 360.0 - diff)
    return angular_distance <= tolerance_degrees


def find_path_via_added(G, source, target):
    """
    Trova un percorso minimo da source a target attraversando solo nodi 'added'
    tra real nodes. Restituisce la lista di nodi del percorso se esiste.
    """
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
    """
    Calcola l'angolo iniziale lungo il percorso da source a target,
    considerando il primo segmento (anche via added).
    """
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


def check_edge_compatibility(G_A, G_B, mapping, angle_tolerance=30):
    """
    Verifica se le connessioni tra i nodi mappati sono compatibili.
    Ora include verifica dell'angolo lungo il percorso diretto o via added.
    """
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

def is_cost_similar(cA, cB, threshold=0.5):
    """Verifica se due costi sono simili entro una soglia relativa"""
    if cA == float('inf') and cB == float('inf'):
        return True
    if cA == float('inf') or cB == float('inf'):
        return False
    if abs(cA) < 1e-6 and abs(cB) < 1e-6:
        return True
    denom = max(abs(cA), abs(cB))
    if denom < 1e-9:
        return True
    try:
        diff_rel = abs(float(cA) - float(cB)) / denom
        return diff_rel <= threshold
    except (ValueError, TypeError):
        return False

def is_ridge_jump_similar(jumpA, jumpB, max_diff=1):
    """Verifica se due scavalcamenti sono simili entro una differenza massima"""
    if jumpA == float('inf') and jumpB == float('inf'):
        return True
    if jumpA == float('inf') or jumpB == float('inf'):
        return False
    try:
        diff = abs(float(jumpA) - float(jumpB))
        return diff <= max_diff
    except (ValueError, TypeError):
        return False

def check_node_compatibility(G_A, G_B, nodeA, nodeB):
    """Verifica se due nodi hanno lo stesso tipo"""
    if not is_real_node(G_A, nodeA) or not is_real_node(G_B, nodeB):
        return False
    
    # Controllo del tipo (ending, bifurcation, etc)
    typeA = G_A.nodes[nodeA].get('type')
    typeB = G_B.nodes[nodeB].get('type')
    return typeA == typeB

def compute_complete_matching_score(G_A, G_B, mapping, M1_A, M1_B, M_scavalcamenti_A, M_scavalcamenti_B, 
                                   cost_weight=1.0, ridge_weight=1.0, angle_weight=1.0):
    """
    Calcola uno score complessivo confrontando TUTTE le coppie di nodi mappati.
    Il punteggio tiene conto di:
    - Differenza nei costi del percorso minimo
    - Differenza nel numero di scavalcamenti (nodi 'added')
    - Differenza negli angoli tra coppie di nodi
    
    Returns:
        float: Score complessivo tra 0.0 (match pessimo) e 1.0 (match perfetto)
        dict: Dettagli per ogni coppia di nodi
    """
    nodes_A = list(mapping.keys())
    total_pairs = 0
    total_score = 0
    pair_details = {}
    
    # Pesi normalizzati
    sum_weights = cost_weight + ridge_weight + angle_weight
    cost_w = cost_weight / sum_weights if sum_weights > 0 else 1/3
    ridge_w = ridge_weight / sum_weights if sum_weights > 0 else 1/3
    angle_w = angle_weight / sum_weights if sum_weights > 0 else 1/3
    
    for i in range(len(nodes_A)):
        nodeA1 = nodes_A[i]
        nodeB1 = mapping[nodeA1]
        
        for j in range(i+1, len(nodes_A)):
            nodeA2 = nodes_A[j]
            nodeB2 = mapping[nodeA2]
            
            # Coppia identificata da (nodeA1, nodeA2)
            pair_id = (nodeA1, nodeA2)
            pair_details[pair_id] = {}
            
            # 1. Score per gli scavalcamenti
            try:
                scA = float(M_scavalcamenti_A[nodeA1][nodeA2])
                scB = float(M_scavalcamenti_B[nodeB1][nodeB2])
                
                # Gestione infinito
                if scA == float('inf') and scB == float('inf'):
                    sc_score = 1.0  # Perfetta compatibilità
                elif scA == float('inf') or scB == float('inf'):
                    sc_score = 0.0  # Totale incompatibilità
                else:
                    # Normalizza la differenza
                    max_sc = max(1, max(scA, scB))
                    sc_diff = abs(scA - scB)
                    sc_score = max(0.0, 1.0 - (sc_diff / max_sc))
                
                pair_details[pair_id]['ridge_score'] = sc_score
                pair_details[pair_id]['ridge_A'] = scA
                pair_details[pair_id]['ridge_B'] = scB
            except (IndexError, TypeError, ValueError):
                # Gestione errori (indici mancanti o valori non validi)
                sc_score = 0.5  # Valore neutro
                pair_details[pair_id]['ridge_score'] = sc_score
                pair_details[pair_id]['error'] = "ridge_calc_error"
            
            # 2. Score per i costi di percorso
            try:
                costA = float(M1_A[nodeA1][nodeA2])
                costB = float(M1_B[nodeB1][nodeB2])
                
                # Gestione infinito
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
                
                # Calcola la differenza angolare minima (considerando che 359° e 1° sono vicini)
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
            
            # Score complessivo per questa coppia (pesato)
            pair_score = (ridge_w * sc_score + cost_w * cost_score + angle_w * angle_score)
            pair_details[pair_id]['total_score'] = pair_score
            
            total_score += pair_score
            total_pairs += 1
    
    # Score medio finale (0-1)
    final_score = total_score / total_pairs if total_pairs > 0 else 0
    
    return final_score, pair_details

def match_subgraph(G_A, G_B, M1_A, M1_B, M_scavalcamenti_A, M_scavalcamenti_B, 
                  cost_threshold_rel=0.5, max_ridge_diff=1, angle_tolerance_degrees=30):
    """
    Verifica se due sottografi sono considerabili match secondo i criteri specificati.
    Calcola anche lo score complessivo per tutte le coppie di nodi mappati.
    
    Args:
        G_A, G_B: i due sottografi da confrontare
        M1_A, M1_B: matrici di costo/distanza tra i nodi
        M_scavalcamenti_A, M_scavalcamenti_B: matrici con il numero di nodi added attraversati
        cost_threshold_rel: soglia relativa per considerare simili i costi
        max_ridge_diff: differenza massima accettabile per gli scavalcamenti
        angle_tolerance_degrees: tolleranza angolare in gradi
        
    Returns:
        success: True se i sottografi sono match, False altrimenti
        mapping: dizionario che mappa i nodi di G_A in G_B
        score: punteggio complessivo del match (0-1, dove 1 è perfetto)
        details: dettagli del punteggio per ogni coppia
    """
    # Ottieni tutti i nodi reali
    real_nodes_A = get_real_nodes(G_A)
    real_nodes_B = get_real_nodes(G_B)
    
    # Se il numero di nodi reali è diverso, non possono essere match
    if len(real_nodes_A) != len(real_nodes_B):
        return False, {}, 0.0, {}
    
    # Prova tutte le permutazioni possibili di mapping
    best_mapping = None
    best_score = -1
    best_details = {}
    
    def try_mapping(mapping=None, idx=0):
        if mapping is None:
            mapping = {}
        
        # Se abbiamo mappato tutti i nodi, verifichiamo la compatibilità
        if idx == len(real_nodes_A):
            # Verifica la compatibilità delle connessioni
            if not check_edge_compatibility(G_A, G_B, mapping):
                return False, None
            
            # Verifica la compatibilità di costi e scavalcamenti
            for nodeA, nodeB in mapping.items():
                for nA in get_real_neighbors_via_added(G_A, nodeA):
                    if nA not in mapping:
                        continue
                    
                    nB = mapping[nA]
                    
                    # Verifica gli scavalcamenti
                    try:
                        scA = M_scavalcamenti_A[nodeA][nA]
                        scB = M_scavalcamenti_B[nodeB][nB]
                        if not is_ridge_jump_similar(scA, scB, max_ridge_diff):
                            return False, None
                    except (KeyError, TypeError):
                        pass
                    
                    # Verifica i costi
                    try:
                        costA = M1_A[nodeA][nA]
                        costB = M1_B[nodeB][nB]
                        if not is_cost_similar(costA, costB, cost_threshold_rel):
                            return False, None
                    except (KeyError, TypeError):
                        pass
                    
                    # Verifica gli angoli
                    try:
                        posA1 = G_A.nodes[nodeA]['pos']
                        posA2 = G_A.nodes[nA]['pos']
                        posB1 = G_B.nodes[nodeB]['pos']
                        posB2 = G_B.nodes[nB]['pos']
                        angA = calculate_angle(posA1, posA2)
                        angB = calculate_angle(posB1, posB2)
                        if not is_angle_similar(angA, angB, angle_tolerance_degrees):
                            return False, None
                    except (KeyError, TypeError):
                        pass
            
            # Se arriviamo qui, il mapping è valido
            return True, mapping.copy()
        
        # Prova a mappare il nodo corrente con tutti i nodi non ancora mappati
        nodeA = real_nodes_A[idx]
        for nodeB in real_nodes_B:
            # Salta se nodeB è già mappato
            if nodeB in mapping.values():
                continue
            
            # Verifica la compatibilità del tipo di nodo
            if not check_node_compatibility(G_A, G_B, nodeA, nodeB):
                continue
            
            # Prova questo mapping
            mapping[nodeA] = nodeB
            success, result_mapping = try_mapping(mapping, idx + 1)
            if success:
                return True, result_mapping
            
            # Backtrack
            del mapping[nodeA]
        
        # Nessun mapping valido trovato
        return False, None
    
    # Avvia il processo di mapping
    success, mapping = try_mapping()
    
    # Se abbiamo trovato un mapping valido, calcola lo score completo
    if success:
        score, details = compute_complete_matching_score(
            G_A, G_B, mapping, M1_A, M1_B, M_scavalcamenti_A, M_scavalcamenti_B
        )
        return success, mapping, score, details
    else:
        return False, {}, 0.0, {}

