
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
            if found:
                break
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

def check_edge_compatibility(G_A, G_B, mapping):
    """
    Verifica se le connessioni tra i nodi mappati sono compatibili.
    Considera equivalenti le connessioni dirette e quelle tramite nodi added.
    """
    for nodeA, nodeB in mapping.items():
        # Ottieni i vicini reali di nodeA (sia diretti che tramite added)
        neighborsA = get_real_neighbors_via_added(G_A, nodeA)
        
        # Ottieni i vicini reali di nodeB (sia diretti che tramite added)
        neighborsB = get_real_neighbors_via_added(G_B, nodeB)
        
        # Per ogni vicino di A che è anche mappato, verifica che esista la corrispondenza in B
        for nA in neighborsA:
            if nA in mapping:
                nB = mapping[nA]
                if nB not in neighborsB:
                    return False
    
    return True

def match_subgraph(G_A, G_B, M1_A, M1_B, M_scavalcamenti_A, M_scavalcamenti_B, 
                  cost_threshold_rel=0.5, max_ridge_diff=1, angle_tolerance_degrees=30):
    """
    Verifica se due sottografi sono considerabili match secondo i criteri specificati.
    
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
    """


    # Verifica preliminare: almeno uno dei due sottografi deve contenere nodi added
    # has_added_A = any(not is_real_node(G_A, node) for node in G_A.nodes())
    # has_added_B = any(not is_real_node(G_B, node) for node in G_B.nodes())
    
    # if not (has_added_A or has_added_B):
    #     return False, {}

    # Ottieni tutti i nodi reali
    real_nodes_A = get_real_nodes(G_A)
    real_nodes_B = get_real_nodes(G_B)
    
    # Se il numero di nodi reali è diverso, non possono essere match
    if len(real_nodes_A) != len(real_nodes_B):
        return False, {}
    
    # Prova tutte le permutazioni possibili di mapping
    # Nota: per grafi grandi, questo può essere inefficiente e potrebbe richiedere
    # un approccio più euristico o di backtracking ottimizzato.
    
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
                        # Se non abbiamo informazioni sugli scavalcamenti, ignoriamo questa verifica
                        pass
                    
                    # Verifica i costi
                    try:
                        costA = M1_A[nodeA][nA]
                        costB = M1_B[nodeB][nB]
                        if not is_cost_similar(costA, costB, cost_threshold_rel):
                            return False, None
                    except (KeyError, TypeError):
                        # Se non abbiamo informazioni sui costi, ignoriamo questa verifica
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
                        # Se non abbiamo informazioni sulla posizione, ignoriamo questa verifica
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
    
    # Verifica aggiuntiva: almeno uno dei due sottografi deve contenere nodi added
    # if success:
    #     has_added_A = any(not is_real_node(G_A, node) for node in G_A.nodes())
    #     has_added_B = any(not is_real_node(G_B, node) for node in G_B.nodes())
        
    #     if not (has_added_A or has_added_B):
    #         return False, {}
    
    return success, mapping

def match_subgraphs_wrapper(G_A, G_B, M1_A, M1_B, M_scavalcamenti_A, M_scavalcamenti_B,
                          cost_threshold_rel=0.5, max_ridge_diff=1, angle_tolerance_degrees=30):
    """
    Wrapper per match_subgraph che restituisce solo il risultato booleano.
    Restituisce True solo se i sottografi sono match e almeno uno dei due contiene nodi added.
    """
    success, _ = match_subgraph(G_A, G_B, M1_A, M1_B, M_scavalcamenti_A, M_scavalcamenti_B,
                             cost_threshold_rel, max_ridge_diff, angle_tolerance_degrees)
    return success

