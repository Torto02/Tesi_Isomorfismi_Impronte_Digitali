import os
import json
import networkx as nx
import math
import matplotlib.pyplot as plt

##############################
# 1) Definisci le funzioni per il matching
##############################

def is_cost_similar(cA, cB, threshold=0.5):
    """
    Ritorna True se cA e cB differiscono meno di 'threshold' (relativo).
    """
    if cA == float('inf') and cB == float('inf'):
        return True
    if cA == float('inf') or cB == float('inf'):
        return False

    denom = max(abs(cA), abs(cB), 1e-9)
    diff = abs(cA - cB) / denom
    return diff <= threshold

def is_ridge_jump_similar(jumpA, jumpB, max_diff=2):
    if jumpA == float('inf') and jumpB == float('inf'):
        return True
    if jumpA == float('inf') or jumpB == float('inf'):
        return False
    return abs(jumpA - jumpB) <= max_diff

def match_subgraphs(
    G_A, G_B,
    M1_A, M2_A, M4_A,  # le matrici di A
    M1_B, M2_B, M4_B,  # le matrici di B
    nodeA, nodeB,
    mapping=None,
    visited_pairs=None,
    cost_threshold=0.1,
    max_ridge_diff=2
):
    if mapping is None:
        mapping = {}
    if visited_pairs is None:
        visited_pairs = set()

    if (nodeA, nodeB) in visited_pairs:
        return True
    visited_pairs.add((nodeA, nodeB))

    # 1) tipi di nodo uguali
    if G_A.nodes[nodeA].get('type') != G_B.nodes[nodeB].get('type'):
        return False

    # 2) Aggiungiamo al mapping
    if nodeA in mapping and mapping[nodeA] != nodeB:
        return False
    mapping[nodeA] = nodeB

    # 3) DFS parallelo sui vicini
    neighborsA = list(G_A[nodeA])
    neighborsB = list(G_B[nodeB])

    for nA in neighborsA:
        found_match = False
        for nB in neighborsB:
            # già matchato?
            if nB in mapping.values() and mapping.get(nA, None) != nB:
                continue

            # check M1
            if not is_cost_similar(M1_A[nodeA][nA], M1_B[nodeB][nB], cost_threshold):
                continue
            # check M2
            if not is_cost_similar(M2_A[nodeA][nA], M2_B[nodeB][nB], cost_threshold):
                continue
            # check M4 (±2 salti)
            if not is_ridge_jump_similar(M4_A[nodeA][nA], M4_B[nodeB][nB], max_ridge_diff):
                continue

            # ricorsione
            if match_subgraphs(G_A, G_B,
                               M1_A, M2_A, M4_A,
                               M1_B, M2_B, M4_B,
                               nA, nB, mapping, visited_pairs,
                               cost_threshold, max_ridge_diff):
                found_match = True
                break
        if not found_match:
            return False
    return True
##############################
# 2) Funzioni di supporto
##############################

def single_source_custom_dijkstra(graph, source, weight_func):
    for (u, v) in graph.edges():
        d = graph[u][v]
        d['temp_weight'] = weight_func(u, v, d)
    distances = nx.single_source_dijkstra_path_length(graph, source, weight='temp_weight')
    for (u, v) in graph.edges():
        del graph[u][v]['temp_weight']
    return distances

def get_subgraph_within_radius(G, M3, source_node, radius):
    N = G.number_of_nodes()
    sub_nodes = [j for j in range(N) if M3[source_node][j] <= radius]
    S = G.subgraph(sub_nodes).copy()
    return S

def plot_and_save_subgraph(S, G, source_node, output_folder, filename):
    pos = nx.get_node_attributes(G, 'pos')
    plt.figure(figsize=(8, 6))
    nx.draw_networkx_nodes(S, pos, node_size=50, node_color="red")
    nx.draw_networkx_edges(S, pos, edge_color="black", width=1)
    if source_node in S:
        nx.draw_networkx_nodes(S, pos, nodelist=[source_node],
                               node_size=50, node_color="green")
    nx.draw_networkx_labels(S, pos, labels={n: str(n) for n in S.nodes()},
                            font_size=3, font_color="black")

    plt.title(f"Sottografo attorno al nodo {source_node}")
    plt.axis("off")

    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, filename)
    plt.savefig(output_path, dpi=600)
    plt.close()
    print(f"Immagine del sottografo salvata in: {output_path}")

def save_matrix_to_file(matrix, filename):
    with open(filename, 'w') as f:
        for row in matrix:
            f.write(','.join(map(str, row)) + '\n')

def plot_mapping(S_A, S_B, G_A, G_B, mapping, output_folder, filename):
    """
    Visualizza il mapping tra due sottografi, mostrando le corrispondenze trovate.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Plot sottografo A
    pos_A = nx.get_node_attributes(G_A, 'pos')
    nx.draw_networkx_nodes(S_A, pos_A, node_size=50, node_color='lightblue', ax=ax1)
    nx.draw_networkx_edges(S_A, pos_A, edge_color='gray', width=1, ax=ax1)
    nx.draw_networkx_labels(S_A, pos_A, labels={n: str(n) for n in S_A.nodes()},
                          font_size=8, font_color="black", ax=ax1)
    
    # Evidenzia i nodi mappati in A
    mapped_nodes_A = list(mapping.keys())
    if mapped_nodes_A:
        nx.draw_networkx_nodes(S_A, pos_A, nodelist=mapped_nodes_A,
                             node_size=100, node_color='red', ax=ax1)
    
    ax1.set_title("Sottografo A")
    ax1.axis('off')
    
    # Plot sottografo B
    pos_B = nx.get_node_attributes(G_B, 'pos')
    nx.draw_networkx_nodes(S_B, pos_B, node_size=50, node_color='lightblue', ax=ax2)
    nx.draw_networkx_edges(S_B, pos_B, edge_color='gray', width=1, ax=ax2)
    nx.draw_networkx_labels(S_B, pos_B, labels={n: str(n) for n in S_B.nodes()},
                          font_size=8, font_color="black", ax=ax2)
    
    # Evidenzia i nodi mappati in B
    mapped_nodes_B = list(mapping.values())
    if mapped_nodes_B:
        nx.draw_networkx_nodes(S_B, pos_B, nodelist=mapped_nodes_B,
                             node_size=100, node_color='red', ax=ax2)
    
    ax2.set_title("Sottografo B")
    ax2.axis('off')
    
    plt.tight_layout()
    
    # Salva l'immagine
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, filename)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Mapping visualizzato salvato in: {output_path}")
##############################
# 3) Funzione per caricare una singola impronta e calcolare M1, M2, M3
##############################

def load_fingerprint_and_compute(folder_path):
    """
    Carica una singola impronta da folder_path, costruisce G,
    calcola M1, M2, M3, M4 e SALVA le quattro matrici in /OutputMatrices/<nomeImpronta>.
    Se le matrici esistono già, le carica direttamente senza ricalcolarle.
    Ritorna (G, M1, M2, M3, M4).
    """
    # Carica i file JSON
    nodes_file = os.path.join(folder_path, "nodes_graph.json")
    edges_file = os.path.join(folder_path, "edges_graph.json")

    if not os.path.exists(nodes_file) or not os.path.exists(edges_file):
        print(f"Errore: File nodes_graph.json o edges_graph.json non trovati in {folder_path}.")
        return None, None, None, None, None

    # Verifica se le matrici esistono già
    out_folder = "/Users/riccardotortorelli/Desktop/Tesi/OutputMatrices"
    impronta_nome = os.path.basename(folder_path)
    sub_folder = os.path.join(out_folder, impronta_nome)
    
    m1_path = os.path.join(sub_folder, "M1.csv")
    m2_path = os.path.join(sub_folder, "M2.csv")
    m3_path = os.path.join(sub_folder, "M3.csv")
    m4_path = os.path.join(sub_folder, "M4.csv")
    
    # Costruisci il grafo in ogni caso (serve per il resto del programma)
    with open(nodes_file, 'r') as f:
        nodes_data = json.load(f)
    with open(edges_file, 'r') as f:
        edges_data = json.load(f)

    nodes = nodes_data['nodes']
    edges = edges_data['edges']

    G = nx.Graph()
    for i, node in enumerate(nodes):
        coord = tuple(node.get('coordinates', [0, 0]))
        ntype = node.get('type', 'unknown')
        G.add_node(i, pos=coord, type=ntype)

    for edge in edges:
        node1, node2 = edge['nodes']
        etype = edge.get('type', 'edge')
        dist = edge.get('distance', None)
        if node1 < len(nodes) and node2 < len(nodes):
            G.add_edge(node1, node2, type=etype, distance=dist)
        else:
            print(f"Attenzione: arco con nodi {edge['nodes']} non valido.")
    
    # Se tutte le matrici esistono, caricale
    if os.path.exists(m1_path) and os.path.exists(m2_path) and os.path.exists(m3_path) and os.path.exists(m4_path):
        print(f"\nMatrici già esistenti per {impronta_nome}, caricamento in corso...")
        
        # Funzione per caricare una matrice da file CSV
        def load_matrix_from_file(file_path):
            matrix = []
            with open(file_path, 'r') as f:
                for line in f:
                    row = [float(val) if val != 'inf' else float('inf') for val in line.strip().split(',')]
                    matrix.append(row)
            return matrix
        
        M1 = load_matrix_from_file(m1_path)
        M2 = load_matrix_from_file(m2_path)
        M3 = load_matrix_from_file(m3_path)
        M4 = load_matrix_from_file(m4_path)
        
        print(f"Matrici caricate con successo da: {sub_folder}")
        return G, M1, M2, M3, M4
    
    # Altrimenti, calcola le matrici
    print(f"\nCalcolo delle matrici per {impronta_nome}...")
    
    # Definizione delle 2 funzioni di peso
    def weight_function_m1(u, v, d):
        arco_type = d.get('type')
        if arco_type == 'added':
            return 1.0
        elif arco_type == 'border':
            return 5.0
        else:
            return 0.0001

    def weight_function_m2(u, v, d):
        if d.get('type') == 'added':
            pos_u = G.nodes[u]['pos']
            pos_v = G.nodes[v]['pos']
            return math.dist(pos_u, pos_v)
        else:
            dist_attr = d.get('distance')
            if dist_attr is not None:
                return dist_attr
            else:
                pos_u = G.nodes[u]['pos']
                pos_v = G.nodes[v]['pos']
                return math.dist(pos_u, pos_v)

    N = G.number_of_nodes()

    # Calcolo M1
    M1 = [[float('inf')] * N for _ in range(N)]
    for node_start in G.nodes():
        dist_dict = single_source_custom_dijkstra(G, node_start, weight_function_m1)
        for node_end, dist_val in dist_dict.items():
            M1[node_start][node_end] = dist_val

    # Calcolo M2
    M2 = [[float('inf')] * N for _ in range(N)]
    for node_start in G.nodes():
        dist_dict = single_source_custom_dijkstra(G, node_start, weight_function_m2)
        for node_end, dist_val in dist_dict.items():
            M2[node_start][node_end] = dist_val

    # Calcolo M3
    M3 = [[0.0] * N for _ in range(N)]
    coords = [G.nodes[i]['pos'] for i in range(N)]
    for i in range(N):
        for j in range(N):
            if i == j:
                M3[i][j] = 0.0
            else:
                M3[i][j] = math.dist(coords[i], coords[j])

    # Calcolo M4
    M4 = [[float('inf')] * N for _ in range(N)]
    for node_start in G.nodes():
        dist_dict = nx.single_source_shortest_path_length(G, node_start)
        for node_end, dist_val in dist_dict.items():
            M4[node_start][node_end] = dist_val

    # Salviamo le matrici
    os.makedirs(sub_folder, exist_ok=True)
    
    # Funzione per salvare una matrice con gestione di inf
    def save_matrix_to_file(matrix, filename):
        with open(filename, 'w') as f:
            for row in matrix:
                f.write(','.join(map(lambda x: str(x) if x != float('inf') else 'inf', row)) + '\n')
    
    save_matrix_to_file(M1, m1_path)
    save_matrix_to_file(M2, m2_path)
    save_matrix_to_file(M3, m3_path)
    save_matrix_to_file(M4, m4_path)
    
    print(f"M1, M2, M3, M4 salvate in: {sub_folder}")
    return G, M1, M2, M3, M4
   

# from itertools import combinations


# def get_sub_subgraphs_of_minutiae(S, size=4):
#     """
#     Genera sottografi di S composti esclusivamente da 'size' minuzie 'vere',
#     escludendo dal calcolo della connettività gli archi di tipo 'added'.
#     Ritorna una lista di (set_of_nodes, subgraph).
#     """
#     # Filtra i nodi di tipo 'ending' o 'bifurcation'
#     real_minutiae = [n for n in S.nodes() if S.nodes[n].get('type') in ('ending', 'bifurcation')]

#     # Crea un grafo privo degli archi 'added'
#     S_no_added = S.copy()
#     edges_to_remove = [(u, v) for (u, v, data) in S.edges(data=True) 
#                        if data.get('type') == 'added']
#     S_no_added.remove_edges_from(edges_to_remove)

#     subgraphs = []
#     from itertools import combinations
#     for subset in combinations(real_minutiae, size):
#         subG = S_no_added.subgraph(subset).copy()
        
#         # Verifichiamo che il sottografo (senza archi 'added') sia connesso
#         if nx.is_connected(subG):
#             subgraphs.append((subset, subG))
    
#     return subgraphs

##############################

def get_connected_subgraphs_of_minutiae(S, size=4):
    """
    Genera tutti i sottografi connessi di S composti esclusivamente da 'size' minuzie 'vere',
    escludendo dal calcolo della connettività gli archi di tipo 'added'.
    
    Restituisce una lista di tuple (set_di_nodi, sottografo_indotto).
    """
    # Filtra i nodi reali (minuzie)
    real_minutiae = [n for n in S.nodes() if S.nodes[n].get('type') in ('ending', 'bifurcation')]

    # Crea un grafo privo degli archi 'added'
    S_no_added = S.copy()
    edges_to_remove = [(u, v) for (u, v, data) in S.edges(data=True) if data.get('type') == 'added']
    S_no_added.remove_edges_from(edges_to_remove)
    
    # Limitiamo il grafo ai soli nodi real_minutiae
    S_minutiae = S_no_added.subgraph(real_minutiae).copy()
    
    risultati = set()  # useremo un set di frozenset per evitare duplicati

    def expand(current_set, candidates):
        if len(current_set) == size:
            risultati.add(frozenset(current_set))
            return
        for node in list(candidates):
            new_current = current_set | {node}
            # Le nuove candidate sono: quelle già in candidates unite ai vicini del nodo appena aggiunto,
            # escludendo i nodi già presenti in new_current.
            new_candidates = (candidates | set(S_minutiae.neighbors(node))) - new_current
            expand(new_current, new_candidates)
    
    # Per ogni nodo, inizia l'espansione creando un sottografo connesso
    for node in S_minutiae.nodes():
        expand({node}, set(S_minutiae.neighbors(node)))
    
    # Costruiamo la lista dei sottografi: per ogni insieme di nodi, estraiamo il sottografo corrispondente.
    subgraphs = [(tuple(sorted(list(s))), S_minutiae.subgraph(s).copy()) for s in risultati]
    return subgraphs


# 4) Funzione principale che carica e confronta due impronte
##############################
def main():
    base_folder = "/Users/riccardotortorelli/Desktop/Tesi/Archivio"
    if not os.path.exists(base_folder):
        print("Errore: La cartella specificata non esiste.")
        return

    # Carica 2 impronte
    impronte_disponibili = sorted([d for d in os.listdir(base_folder)
                                   if os.path.isdir(os.path.join(base_folder, d))])
    if len(impronte_disponibili) < 2:
        print("Servono almeno 2 impronte nella cartella.")
        return

    # Scegli impronta A
    print("\nImpronte disponibili:")
    for idx, nome in enumerate(impronte_disponibili):
        print(f"{idx + 1}. {nome}")

    while True:
        try:
            sceltaA = int(input("\nSeleziona il numero dell'impronta A: ")) - 1
            if 0 <= sceltaA < len(impronte_disponibili):
                improntaA_selezionata = impronte_disponibili[sceltaA]
                break
            else:
                print("Selezione non valida per A.")
        except ValueError:
            print("Errore: inserisci un numero valido.")

    folder_A = os.path.join(base_folder, improntaA_selezionata)
    G_A, M1_A, M2_A, M3_A, M4_A = load_fingerprint_and_compute(folder_A)
    if G_A is None:
        print("Impossibile caricare impronta A.")
        return

    # Scegli impronta B
    while True:
        try:
            sceltaB = int(input("\nSeleziona il numero dell'impronta B: ")) - 1
            if 0 <= sceltaB < len(impronte_disponibili):
                improntaB_selezionata = impronte_disponibili[sceltaB]
                break
            else:
                print("Selezione non valida per B.")
        except ValueError:
            print("Errore: inserisci un numero valido.")

    folder_B = os.path.join(base_folder, improntaB_selezionata)
    G_B, M1_B, M2_B, M3_B, M4_B = load_fingerprint_and_compute(folder_B)
    if G_B is None:
        print("Impossibile caricare impronta B.")
        return

    print(f"\nImpronta A = {improntaA_selezionata}, #nodi={G_A.number_of_nodes()}, #archi={G_A.number_of_edges()}")
    print(f"Impronta B = {improntaB_selezionata}, #nodi={G_B.number_of_nodes()}, #archi={G_B.number_of_edges()}")

    # Estrai un "macro-sottografo" S_A e S_B (ad esempio un raggio in M3)
    # Improved minutiae selection for impronta A
    minutia_nodesA = [n for n in G_A.nodes() if G_A.nodes[n]['type'] in ('ending','bifurcation')]
    if not minutia_nodesA:
        print("Nessuna minuzia trovata in A.")
        return
    
    # Display available minutiae with their types and positions
    print(f"\nMinuzie disponibili in {improntaA_selezionata}:")
    for idx, node_id in enumerate(minutia_nodesA):
        node_type = G_A.nodes[node_id]['type']
        node_pos = G_A.nodes[node_id]['pos']
        print(f"{idx + 1}. Nodo {node_id} - Tipo: {node_type}, Posizione: {node_pos}")
    
    # Let user select a minutia
    # while True:
    #     try:
    #         minutia_idx = int(input(f"\nSeleziona il numero della minuzia per {improntaA_selezionata} (1-{len(minutia_nodesA)}): ")) - 1
    #         if 0 <= minutia_idx < len(minutia_nodesA):
    #             minuziaA = minutia_nodesA[minutia_idx]
    #             print(f"Hai selezionato il nodo {minuziaA} di tipo {G_A.nodes[minuziaA]['type']}")
    #             break
    #         else:
    #             print(f"Selezione non valida. Inserisci un numero tra 1 e {len(minutia_nodesA)}.")
    #     except ValueError:
    #         print("Errore: inserisci un numero valido.")
    
    # max_dist_A = max(max(row) for row in M3_A if max(row) < float('inf'))
    # radiusA = 0.1 * max_dist_A
    # S_A = get_subgraph_within_radius(G_A, M3_A, minuziaA, radiusA)
    # print(f"Sottografo S_A con raggio={radiusA:.2f}, nodi={S_A.number_of_nodes()}, archi={S_A.number_of_edges()}")
    
    # # Salva il macro-sottografo S_A
    # out_graphs = "/Users/riccardotortorelli/Desktop/Tesi/OutputGraph"
    # os.makedirs(out_graphs, exist_ok=True)
    # plot_and_save_subgraph(S_A, G_A, minuziaA, out_graphs, f"macro_subgraph_A_{improntaA_selezionata}_nodo{minuziaA}.png")

    # # Similar improvement for impronta B
    # minutia_nodesB = [n for n in G_B.nodes() if G_B.nodes[n]['type'] in ('ending','bifurcation')]
    # if not minutia_nodesB:
    #     print("Nessuna minuzia trovata in B.")
    #     return
    
    # print(f"\nMinuzie disponibili in {improntaB_selezionata}:")
    # for idx, node_id in enumerate(minutia_nodesB):
    #     node_type = G_B.nodes[node_id]['type']
    #     node_pos = G_B.nodes[node_id]['pos']
    #     print(f"{idx + 1}. Nodo {node_id} - Tipo: {node_type}, Posizione: {node_pos}")
    
    # while True:
    #     try:
    #         minutia_idx = int(input(f"\nSeleziona il numero della minuzia per {improntaB_selezionata} (1-{len(minutia_nodesB)}): ")) - 1
    #         if 0 <= minutia_idx < len(minutia_nodesB):
    #             minuziaB = minutia_nodesB[minutia_idx]
    #             print(f"Hai selezionato il nodo {minuziaB} di tipo {G_B.nodes[minuziaB]['type']}")
    #             break
    #         else:
    #             print(f"Selezione non valida. Inserisci un numero tra 1 e {len(minutia_nodesB)}.")
    #     except ValueError:
    #         print("Errore: inserisci un numero valido.")
    
    # max_dist_B = max(max(row) for row in M3_B if max(row) < float('inf'))
    # radiusB = 0.33 * max_dist_B
    # S_B = get_subgraph_within_radius(G_B, M3_B, minuziaB, radiusB)
    # print(f"Sottografo S_B con raggio={radiusB:.2f}, nodi={S_B.number_of_nodes()}, archi={S_B.number_of_edges()}")
    
    # # Salva il macro-sottografo S_B
    # plot_and_save_subgraph(S_B, G_B, minuziaB, out_graphs, f"macro_subgraph_B_{improntaB_selezionata}_nodo{minuziaB}.png")

    
    # Let user select a minutia
    while True:
        try:
            minutia_idx = int(input(f"\nSeleziona il numero della minuzia per {improntaA_selezionata} (1-{len(minutia_nodesA)}): ")) - 1
            if 0 <= minutia_idx < len(minutia_nodesA):
                minuziaA = minutia_nodesA[minutia_idx]
                print(f"Hai selezionato il nodo {minuziaA} di tipo {G_A.nodes[minuziaA]['type']}")
                break
            else:
                print(f"Selezione non valida. Inserisci un numero tra 1 e {len(minutia_nodesA)}.")
        except ValueError:
            print("Errore: inserisci un numero valido.")
    
    max_dist_A = max(max(row) for row in M3_A if max(row) < float('inf'))
    radiusA = 0.1 * max_dist_A
    S_A = get_subgraph_within_radius(G_A, M3_A, minuziaA, radiusA)
    print(f"Sottografo S_A con raggio={radiusA:.2f}, nodi={S_A.number_of_nodes()}, archi={S_A.number_of_edges()}")
    
    # Salva il macro-sottografo S_A
    out_graphs = "/Users/riccardotortorelli/Desktop/Tesi/OutputGraph"
    os.makedirs(out_graphs, exist_ok=True)
    plot_and_save_subgraph(S_A, G_A, minuziaA, out_graphs, f"macro_subgraph_A_{improntaA_selezionata}_nodo{minuziaA}.png")

    # Automatic selection for impronta B based on spatial position
    minutia_nodesB = [n for n in G_B.nodes() if G_B.nodes[n]['type'] in ('ending','bifurcation')]
    if not minutia_nodesB:
        print("Nessuna minuzia trovata in B.")
        return
    
    # Get position of selected minutia in A
    posA = G_A.nodes[minuziaA]['pos']
    
    # Find closest minutia in B based on spatial position
    closest_minutiaB = None
    min_distance = float('inf')
    
    for node_id in minutia_nodesB:
        posB = G_B.nodes[node_id]['pos']
        distance = math.dist(posA, posB)
        if distance < min_distance:
            min_distance = distance
            closest_minutiaB = node_id
    
    minuziaB = closest_minutiaB
    print(f"\nSelezionata automaticamente la minuzia più vicina in {improntaB_selezionata}:")
    print(f"Nodo {minuziaB} di tipo {G_B.nodes[minuziaB]['type']}")
    print(f"Distanza spaziale dalla minuzia A: {min_distance:.2f}")
    
    max_dist_B = max(max(row) for row in M3_B if max(row) < float('inf'))
    radiusB = 0.33 * max_dist_B
    S_B = get_subgraph_within_radius(G_B, M3_B, minuziaB, radiusB)
    print(f"Sottografo S_B con raggio={radiusB:.2f}, nodi={S_B.number_of_nodes()}, archi={S_B.number_of_edges()}")
    
    # Salva il macro-sottografo S_B
    plot_and_save_subgraph(S_B, G_B, minuziaB, out_graphs, f"macro_subgraph_B_{improntaB_selezionata}_nodo{minuziaB}.png")

    # -------------- DA QUI IL MATCH SOLO SUI SOTTO-SOTTOGRAFI ---------------

    sub_subgraphs_A = get_connected_subgraphs_of_minutiae(S_A, size=4)
    sub_subgraphs_B = get_connected_subgraphs_of_minutiae(S_B, size=4)


    print(f"\nIn S_A abbiamo {len(sub_subgraphs_A)} sotto-sottografi (4 minuzie).")
    print(f"In S_B abbiamo {len(sub_subgraphs_B)} sotto-sottografi (4 minuzie).")
    out_subgraphs = "/Users/riccardotortorelli/Desktop/Tesi/OutputSubgraphs"
    os.makedirs(out_subgraphs, exist_ok=True)

    match_counter = 0
    # 3) Confrontiamo OGNI sub-sottografo A con OGNI sub-sottografo B
    for (subsetA, subG_A) in sub_subgraphs_A:
        for (subsetB, subG_B) in sub_subgraphs_B:
            # scegliamo un nodo sorgente in subG_A e subG_B
            if not subsetA or not subsetB:
                continue
            nodeA = list(subsetA)[0]
            nodeB = list(subsetB)[0]

            mapping = {}
            success = match_subgraphs(
                subG_A, subG_B,
                M1_A, M2_A, M4_A,
                M1_B, M2_B, M4_B,
                nodeA, nodeB,
                mapping=mapping,
                cost_threshold=0.05,
                max_ridge_diff=2
            )
            if success and len(mapping) == len(subG_A.nodes()):
                match_counter += 1
                print(f"\nTrovato match #{match_counter}!")
                print(f"Nodi in subG_A: {subsetA}, Nodi in subG_B: {subsetB}")
                print("Mapping:", mapping)

                # Plot per debug (opzionale)
                plot_mapping(subG_A, subG_B, G_A, G_B, mapping,
                             out_subgraphs,
                             f"match_{nodeA}_{nodeB}.png")

    print(f"\nTotale match trovati = {match_counter}")
    print("\n--- Elaborazione completata ---")

if __name__ == "__main__":
    main()
