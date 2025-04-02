import os
import json
import networkx as nx
from networkx.algorithms import isomorphism
import math
import matplotlib.pyplot as plt
from itertools import combinations
from multiprocessing import Pool
import logging
from scipy.sparse import csr_matrix

# Configura il logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

###############################################################################
# 1) Funzioni di Supporto
###############################################################################

def single_source_custom_dijkstra(graph, source, weight_func):
    """
    Esegue l'algoritmo di Dijkstra con una funzione di peso personalizzata.
    
    Args:
        graph (nx.Graph): Il grafo su cui calcolare i percorsi.
        source (int): Nodo sorgente.
        weight_func (callable): Funzione per calcolare il peso degli archi.
    
    Returns:
        dict: Dizionario con le distanze dal nodo sorgente.
    """
    for (u, v) in graph.edges():
        d = graph[u][v]
        d['temp_weight'] = weight_func(u, v, d)
    distances = nx.single_source_dijkstra_path_length(graph, source, weight='temp_weight')
    for (u, v) in graph.edges():
        del graph[u][v]['temp_weight']
    return distances

def get_subgraph_within_radius(G, M3, source_node, radius):
    """
    Restituisce il sottografo dei nodi entro un certo raggio dalla sorgente, basato su M3.
    
    Args:
        G (nx.Graph): Grafo completo.
        M3 (numpy.ndarray): Matrice delle distanze euclidee.
        source_node (int): Nodo sorgente.
        radius (float): Raggio massimo.
    
    Returns:
        nx.Graph: Sottografo risultante.
    """
    N = G.number_of_nodes()
    sub_nodes = [j for j in range(N) if M3[source_node][j] <= radius]
    return G.subgraph(sub_nodes).copy()

def plot_and_save_subgraph(S, G, source_node, output_folder, filename):
    """
    Disegna e salva un'immagine del sottografo, evidenziando il nodo sorgente.
    
    Args:
        S (nx.Graph): Sottografo da visualizzare.
        G (nx.Graph): Grafo originale per le posizioni.
        source_node (int): Nodo sorgente da evidenziare.
        output_folder (str): Cartella di output.
        filename (str): Nome del file immagine.
    """
    pos = nx.get_node_attributes(G, 'pos')
    plt.figure(figsize=(8, 6))
    nx.draw_networkx_nodes(S, pos, node_size=50, node_color="red")
    nx.draw_networkx_edges(S, pos, edge_color="black", width=1)
    if source_node in S:
        nx.draw_networkx_nodes(S, pos, nodelist=[source_node], node_size=50, node_color="green")
    nx.draw_networkx_labels(S, pos, labels={n: str(n) for n in S.nodes()}, font_size=3, font_color="black")

    plt.title(f"Sottografo attorno al nodo {source_node}")
    plt.axis("off")

    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, filename)
    plt.savefig(output_path, dpi=600)
    plt.close()
    logging.info(f"Immagine del sottografo salvata in: {output_path}")

def plot_mapping(S_A, S_B, G_A, G_B, mapping, output_folder, filename):
    """
    Visualizza il mapping tra due sottografi, evidenziando le corrispondenze.
    
    Args:
        S_A (nx.Graph): Sottografo A.
        S_B (nx.Graph): Sottografo B.
        G_A (nx.Graph): Grafo originale A per le posizioni.
        G_B (nx.Graph): Grafo originale B per le posizioni.
        mapping (dict): Dizionario del mapping tra nodi.
        output_folder (str): Cartella di output.
        filename (str): Nome del file immagine.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Plot sottografo A
    pos_A = nx.get_node_attributes(G_A, 'pos')
    nx.draw_networkx_nodes(S_A, pos_A, node_size=50, node_color='lightblue', ax=ax1)
    nx.draw_networkx_edges(S_A, pos_A, edge_color='gray', width=1, ax=ax1)
    nx.draw_networkx_labels(S_A, pos_A, labels={n: str(n) for n in S_A.nodes()}, font_size=8, font_color="black", ax=ax1)
    mapped_nodes_A = list(mapping.keys())
    if mapped_nodes_A:
        nx.draw_networkx_nodes(S_A, pos_A, nodelist=mapped_nodes_A, node_size=100, node_color='red', ax=ax1)
    ax1.set_title("Sottografo A")
    ax1.axis('off')
    
    # Plot sottografo B
    pos_B = nx.get_node_attributes(G_B, 'pos')
    nx.draw_networkx_nodes(S_B, pos_B, node_size=50, node_color='lightblue', ax=ax2)
    nx.draw_networkx_edges(S_B, pos_B, edge_color='gray', width=1, ax=ax2)
    nx.draw_networkx_labels(S_B, pos_B, labels={n: str(n) for n in S_B.nodes()}, font_size=8, font_color="black", ax=ax2)
    mapped_nodes_B = list(mapping.values())
    if mapped_nodes_B:
        nx.draw_networkx_nodes(S_B, pos_B, nodelist=mapped_nodes_B, node_size=100, node_color='red', ax=ax2)
    ax2.set_title("Sottografo B")
    ax2.axis('off')
    
    plt.tight_layout()
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, filename)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    logging.info(f"Mapping visualizzato salvato in: {output_path}")

###############################################################################
# 2) Funzioni per Calcolo Matrici e Caricamento Impronte
###############################################################################

def load_fingerprint_and_compute(folder_path):
    """
    Carica un'impronta e calcola (o carica) le matrici M1, M2, M3, M4.
    
    Args:
        folder_path (str): Percorso della cartella dell'impronta.
    
    Returns:
        tuple: (G, M1, M2, M3, M4) - Grafo e matrici associate.
    """
    nodes_file = os.path.join(folder_path, "nodes_graph.json")
    edges_file = os.path.join(folder_path, "edges_graph.json")

    if not os.path.exists(nodes_file) or not os.path.exists(edges_file):
        logging.error(f"File nodes_graph.json o edges_graph.json non trovati in {folder_path}.")
        return None, None, None, None, None

    out_folder = "/Users/riccardotortorelli/Desktop/Tesi/OutputMatrices"
    impronta_nome = os.path.basename(folder_path)
    sub_folder = os.path.join(out_folder, impronta_nome)
    
    m1_path = os.path.join(sub_folder, "M1.csv")
    m2_path = os.path.join(sub_folder, "M2.csv")
    m3_path = os.path.join(sub_folder, "M3.csv")
    m4_path = os.path.join(sub_folder, "M4.csv")
    
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
            logging.warning(f"Arco con nodi {edge['nodes']} non valido.")

    if all(os.path.exists(p) for p in [m1_path, m2_path, m3_path, m4_path]):
        logging.info(f"Matrici già esistenti per {impronta_nome}, caricamento in corso...")
        
        def load_matrix_from_file(file_path):
            matrix = []
            with open(file_path, 'r') as f:
                for line in f:
                    row = [float(val) if val != 'inf' else float('inf') for val in line.strip().split(',')]
                    matrix.append(row)
            return csr_matrix(matrix)
        
        M1 = load_matrix_from_file(m1_path)
        M2 = load_matrix_from_file(m2_path)
        M3 = load_matrix_from_file(m3_path)
        M4 = load_matrix_from_file(m4_path)
        
        logging.info(f"Matrici caricate con successo da: {sub_folder}")
        return G, M1, M2, M3, M4
    
    logging.info(f"Calcolo delle matrici per {impronta_nome}...")
    
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
            return dist_attr if dist_attr is not None else math.dist(G.nodes[u]['pos'], G.nodes[v]['pos'])

    N = G.number_of_nodes()

    M1 = [[float('inf')] * N for _ in range(N)]
    for node_start in G.nodes():
        dist_dict = single_source_custom_dijkstra(G, node_start, weight_function_m1)
        for node_end, dist_val in dist_dict.items():
            M1[node_start][node_end] = dist_val
    M1 = csr_matrix(M1)

    M2 = [[float('inf')] * N for _ in range(N)]
    for node_start in G.nodes():
        dist_dict = single_source_custom_dijkstra(G, node_start, weight_function_m2)
        for node_end, dist_val in dist_dict.items():
            M2[node_start][node_end] = dist_val
    M2 = csr_matrix(M2)

    M3 = [[0.0] * N for _ in range(N)]
    coords = [G.nodes[i]['pos'] for i in range(N)]
    for i in range(N):
        for j in range(N):
            if i != j:
                M3[i][j] = math.dist(coords[i], coords[j])
    M3 = csr_matrix(M3)

    M4 = [[float('inf')] * N for _ in range(N)]
    for node_start in G.nodes():
        dist_dict = nx.single_source_shortest_path_length(G, node_start)
        for node_end, dist_val in dist_dict.items():
            M4[node_start][node_end] = dist_val
    M4 = csr_matrix(M4)

    os.makedirs(sub_folder, exist_ok=True)
    
    def save_matrix_to_file_custom(matrix, filename):
        with open(filename, 'w') as f:
            for row in matrix.toarray():
                f.write(','.join(map(lambda x: str(x) if x != float('inf') else 'inf', row)) + '\n')
    
    save_matrix_to_file_custom(M1, m1_path)
    save_matrix_to_file_custom(M2, m2_path)
    save_matrix_to_file_custom(M3, m3_path)
    save_matrix_to_file_custom(M4, m4_path)
    
    logging.info(f"M1, M2, M3, M4 salvate in: {sub_folder}")
    return G, M1, M2, M3, M4

###############################################################################
# 3) Preprocessing: Calcolo Firma dei Nodi e Filtraggio
###############################################################################

def compute_node_signature(G, node):
    """
    Calcola una firma per il nodo basata su tipo, grado e distanza media dai vicini.
    
    Args:
        G (nx.Graph): Grafo.
        node (int): Nodo per cui calcolare la firma.
    
    Returns:
        tuple: (tipo, grado, distanza_media).
    """
    node_type = G.nodes[node].get('type', 'unknown')
    degree = G.degree[node]
    neighbors = list(G[node])
    if neighbors:
        distances = [G[node][nb].get('distance', math.dist(G.nodes[node]['pos'], G.nodes[nb]['pos'])) for nb in neighbors]
        mean_edge_length = sum(distances) / len(distances)
    else:
        mean_edge_length = 0.0
    return (node_type, degree, round(mean_edge_length, 2))

def assign_signatures_to_all_nodes(G):
    """Assegna una firma a tutti i nodi del grafo."""
    for node in G.nodes():
        G.nodes[node]['signature'] = compute_node_signature(G, node)

def get_relevant_minutiae(S, min_degree=2, max_mean_edge_len=50):
    """
    Filtra le minuzie rilevanti in base a grado e lunghezza media degli archi.
    
    Args:
        S (nx.Graph): Sottografo.
        min_degree (int): Grado minimo.
        max_mean_edge_len (float): Lunghezza media massima.
    
    Returns:
        list: Lista di nodi filtrati.
    """
    return [n for n in S.nodes() if S.nodes[n]['signature'][0] in ('ending', 'bifurcation') and 
            S.nodes[n]['signature'][1] >= min_degree and S.nodes[n]['signature'][2] <= max_mean_edge_len]

# def get_sub_subgraphs_of_minutiae_natural(S, size=6, min_degree=2, max_mean_edge_len=50):
#     """
#     Genera sottografi connessi di dimensione specificata, considerando solo archi naturali per la connettività.
    
#     Args:
#         S (nx.Graph): Sottografo.
#         size (int): Numero di nodi nel sottografo.
#         min_degree (int): Grado minimo.
#         max_mean_edge_len (float): Lunghezza media massima.
    
#     Returns:
#         list: Lista di tuple (nodi, sottografo).
#     """
#     filtered_nodes = get_relevant_minutiae(S, min_degree, max_mean_edge_len)
#     subgraphs = []
#     for subset in combinations(filtered_nodes, size):
#         subG = S.subgraph(subset).copy()
#         subG_natural = subG.copy()
#         edges_to_remove = [(u, v) for u, v in subG_natural.edges() if subG_natural[u][v].get('type') == 'added']
#         subG_natural.remove_edges_from(edges_to_remove)
#         if nx.is_connected(subG_natural):
#             subgraphs.append((subset, subG))
#     return subgraphs

def get_sub_subgraphs_of_minutiae_natural(S, size=6, min_degree=2, max_mean_edge_len=50):
    """
    Genera subsottografi connessi di 'size' nodi, usando solo archi naturali.
    
    Parametri:
    - S: grafo originale
    - size: numero di nodi nei subsottografi
    - min_degree: grado minimo dei nodi
    - max_mean_edge_len: lunghezza media massima degli archi
    """
    # Filtra i nodi rilevanti
    filtered_nodes = get_relevant_minutiae(S, min_degree, max_mean_edge_len)
    subgraphs = []
    
    # Genera tutte le combinazioni di 'size' nodi
    for subset in combinations(filtered_nodes, size):
        # Crea un subsottografo basato sul subset
        subG = S.subgraph(subset).copy()
        
        # Crea una versione "naturale" rimuovendo gli archi 'added'
        subG_natural = subG.copy()
        edges_to_remove = [(u, v) for u, v in subG_natural.edges() if subG_natural[u][v].get('type') == 'added']
        subG_natural.remove_edges_from(edges_to_remove)
        
        # Verifica se il subsottografo naturale è connesso
        if nx.is_connected(subG_natural):
            subgraphs.append((subset, subG_natural))
    
    return subgraphs
###############################################################################
# 4) Funzioni di Matching
###############################################################################

def pre_check_subgraphs(subG_A, subG_B):
    """Controllo preliminare per scartare sottografi non isomorfi."""
    if subG_A.number_of_nodes() != subG_B.number_of_nodes() or subG_A.number_of_edges() != subG_B.number_of_edges():
        return False
    return sorted([d for _, d in subG_A.degree()]) == sorted([d for _, d in subG_B.degree()])

def match_subgraphs(G_A, G_B, M1_A, M2_A, M4_A, M1_B, M2_B, M4_B, nodeA, nodeB, cost_threshold=0.1, max_ridge_diff=2):
    """
    Confronta due sottografi per isomorfismo usando VF2 e verifica con le matrici.
    
    Args:
        G_A, G_B (nx.Graph): Sottografi da confrontare.
        M1_A, M2_A, M4_A (csr_matrix): Matrici di A.
        M1_B, M2_B, M4_B (csr_matrix): Matrici di B.
        nodeA, nodeB (int): Nodi sorgente.
        cost_threshold (float): Soglia per similarità dei costi.
        max_ridge_diff (int): Differenza massima nei salti.
    
    Returns:
        tuple: (successo, mapping).
    """
    if not pre_check_subgraphs(G_A, G_B):
        return False, {}

    GM = isomorphism.GraphMatcher(G_A, G_B, node_match=lambda n1, n2: n1.get('type') == n2.get('type'))
    if GM.subgraph_is_isomorphic():
        mapping = next(GM.subgraph_isomorphisms_iter())
        for nA, nB in mapping.items():
            if not (is_cost_similar(M1_A[nodeA, nA], M1_B[nodeB, nB], cost_threshold) and
                    is_cost_similar(M2_A[nodeA, nA], M2_B[nodeB, nB], cost_threshold) and
                    is_ridge_jump_similar(M4_A[nodeA, nA], M4_B[nodeB, nB], max_ridge_diff)):
                return False, {}
        return True, mapping
    return False, {}

def is_cost_similar(cA, cB, threshold=1):
    """Verifica se due costi sono simili entro una soglia."""
    if cA == float('inf') and cB == float('inf'):
        return True
    if cA == float('inf') or cB == float('inf'):
        return False
    denom = max(abs(cA), abs(cB), 1e-9)
    return abs(cA - cB) / denom <= threshold

def is_ridge_jump_similar(jumpA, jumpB, max_diff=2):
    """Verifica se due salti di cresta sono simili."""
    if jumpA == float('inf') and jumpB == float('inf'):
        return True
    if jumpA == float('inf') or jumpB == float('inf'):
        return False
    return abs(jumpA - jumpB) <= max_diff

###############################################################################
# 5) Funzione di Confronto Parallelo
###############################################################################

def compare_subgraphs(args):
    """Confronta due sottografi in parallelo."""
    (subsetA, subG_A), (subsetB, subG_B), M1_A, M2_A, M4_A, M1_B, M2_B, M4_B = args
    nodeA, nodeB = list(subsetA)[0], list(subsetB)[0]
    success, mapping = match_subgraphs(subG_A, subG_B, M1_A, M2_A, M4_A, M1_B, M2_B, M4_B, nodeA, nodeB)
    return success, mapping, (subsetA, subG_A), (subsetB, subG_B)

###############################################################################
# 6) Funzione Principale
###############################################################################

def main():
    """Funzione principale per il confronto delle impronte."""
    base_folder = "/Users/riccardotortorelli/Desktop/Tesi/Archivio"
    if not os.path.exists(base_folder):
        logging.error("La cartella specificata non esiste.")
        return

    impronte_disponibili = sorted([d for d in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, d))])
    if len(impronte_disponibili) < 2:
        logging.error("Servono almeno 2 impronte nella cartella.")
        return

    print("\nImpronte disponibili:")
    for idx, nome in enumerate(impronte_disponibili):
        print(f"{idx + 1}. {nome}")

    sceltaA = int(input("\nSeleziona il numero dell'impronta A: ")) - 1
    improntaA_selezionata = impronte_disponibili[sceltaA]
    folder_A = os.path.join(base_folder, improntaA_selezionata)
    G_A, M1_A, M2_A, M3_A, M4_A = load_fingerprint_and_compute(folder_A)
    if G_A is None:
        return

    sceltaB = int(input("\nSeleziona il numero dell'impronta B: ")) - 1
    improntaB_selezionata = impronte_disponibili[sceltaB]
    folder_B = os.path.join(base_folder, improntaB_selezionata)
    G_B, M1_B, M2_B, M3_B, M4_B = load_fingerprint_and_compute(folder_B)
    if G_B is None:
        return

    logging.info(f"Impronta A = {improntaA_selezionata}, #nodi={G_A.number_of_nodes()}, #archi={G_A.number_of_edges()}")
    logging.info(f"Impronta B = {improntaB_selezionata}, #nodi={G_B.number_of_nodes()}, #archi={G_B.number_of_edges()}")

    assign_signatures_to_all_nodes(G_A)
    assign_signatures_to_all_nodes(G_B)

    minutia_nodesA = [n for n in G_A.nodes() if G_A.nodes[n]['type'] in ('ending', 'bifurcation')]
    print(f"\nMinuzie disponibili in {improntaA_selezionata}:")
    for idx, node_id in enumerate(minutia_nodesA):
        print(f"{idx + 1}. Nodo {node_id} - Tipo: {G_A.nodes[node_id]['type']}, Posizione: {G_A.nodes[node_id]['pos']}")
    minutia_idx = int(input(f"\nSeleziona il numero della minuzia per {improntaA_selezionata}: ")) - 1
    minuziaA = minutia_nodesA[minutia_idx]

    max_dist_A = max(M3_A.toarray().max(axis=1).tolist()) if M3_A.toarray().max() < float('inf') else 0
    radiusA = 0.04 * max_dist_A
    S_A = get_subgraph_within_radius(G_A, M3_A.toarray(), minuziaA, radiusA)
    logging.info(f"Sottografo S_A: raggio={radiusA:.2f}, nodi={S_A.number_of_nodes()}, archi={S_A.number_of_edges()}")

    out_graphs = "/Users/riccardotortorelli/Desktop/Tesi/OutputGraph"
    plot_and_save_subgraph(S_A, G_A, minuziaA, out_graphs, f"macro_subgraph_A_{improntaA_selezionata}_nodo{minuziaA}.png")

    minutia_nodesB = [n for n in G_B.nodes() if G_B.nodes[n]['type'] in ('ending', 'bifurcation')]
    print(f"\nMinuzie disponibili in {improntaB_selezionata}:")
    for idx, node_id in enumerate(minutia_nodesB):
        print(f"{idx + 1}. Nodo {node_id} - Tipo: {G_B.nodes[node_id]['type']}, Posizione: {G_B.nodes[node_id]['pos']}")
    minutia_idx = int(input(f"\nSeleziona il numero della minuzia per {improntaB_selezionata}: ")) - 1
    minuziaB = minutia_nodesB[minutia_idx]

    max_dist_B = max(M3_B.toarray().max(axis=1).tolist()) if M3_B.toarray().max() < float('inf') else 0
    radiusB = 0.04 * max_dist_B
    S_B = get_subgraph_within_radius(G_B, M3_B.toarray(), minuziaB, radiusB)
    logging.info(f"Sottografo S_B: raggio={radiusB:.2f}, nodi={S_B.number_of_nodes()}, archi={S_B.number_of_edges()}")

    plot_and_save_subgraph(S_B, G_B, minuziaB, out_graphs, f"macro_subgraph_B_{improntaB_selezionata}_nodo{minuziaB}.png")

    sub_subgraphs_A = get_sub_subgraphs_of_minutiae_natural(S_A)
    sub_subgraphs_B = get_sub_subgraphs_of_minutiae_natural(S_B)
    logging.info(f"In S_A: {len(sub_subgraphs_A)} sotto-sottografi.")
    logging.info(f"In S_B: {len(sub_subgraphs_B)} sotto-sottografi.")

    out_subgraphs = "/Users/riccardotortorelli/Desktop/Tesi/OutputSubgraphs"
    args_list = [(subA, subB, M1_A, M2_A, M4_A, M1_B, M2_B, M4_B) for subA in sub_subgraphs_A for subB in sub_subgraphs_B]

    with Pool() as pool:
        results = pool.map(compare_subgraphs, args_list)

    match_counter = 0
    for success, mapping, (subsetA, subG_A), (subsetB, subG_B) in results:
        if success and len(mapping) == len(subG_A.nodes()):
            match_counter += 1
            logging.info(f"Trovato match #{match_counter}!")
            logging.info(f"Nodi in subG_A: {subsetA}, Nodi in subG_B: {subsetB}")
            logging.info(f"Mapping: {mapping}")
            plot_mapping(subG_A, subG_B, G_A, G_B, mapping, out_subgraphs, f"match_{match_counter}.png")

    logging.info(f"Totale match trovati = {match_counter}")
    print("\n--- Elaborazione completata ---")

if __name__ == "__main__":
    main()