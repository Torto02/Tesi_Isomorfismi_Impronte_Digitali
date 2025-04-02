import os
import json
import networkx as nx
import math

# --- Funzioni di supporto per il calcolo delle matrici ---

def single_source_custom_dijkstra(graph, source, weight_func):
    """
    Esegue una dijkstra personalizzata su 'graph' a partire da 'source',
    usando 'weight_func' come funzione per calcolare il peso di ogni arco.
    Ritorna un dizionario {nodo_destinazione: distanza}.
    """
    # Aggiunge la chiave 'temp_weight' ai singoli archi per lanciare la dijkstra nativa di networkx.
    for (u, v) in graph.edges():
        d = graph[u][v]
        d['temp_weight'] = weight_func(u, v, d)
    
    # Gestione del caso in cui il nodo source sia isolato
    try:
        distances = nx.single_source_dijkstra_path_length(graph, source, weight='temp_weight')
    except nx.NetworkXNoPath:
        # Se non ci sono percorsi dal nodo source (es. isolato), ritorna solo la distanza a se stesso
        distances = {source: 0.0} 
        print(f"Attenzione: Nessun percorso trovato da nodo {source} in single_source_custom_dijkstra.")

    # Ripulisce la chiave 'temp_weight'
    for (u, v) in graph.edges():
        # Verifica se la chiave 'temp_weight' esiste prima di eliminarla
        if 'temp_weight' in graph[u][v]:
             del graph[u][v]['temp_weight']
             
    return distances

def load_matrix_from_file(file_path):
    """Carica una matrice da un file CSV."""
    matrix = []
    with open(file_path, 'r') as f:
        for line in f:
            row = [float(val) if val != 'inf' else float('inf')
                   for val in line.strip().split(',')]
            matrix.append(row)
    return matrix

def save_matrix_to_file(matrix, filename):
    """Salva una matrice (lista di liste) su file CSV, gestendo 'inf'."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as f:
        for row in matrix:
            f.write(','.join(
                str(x) if x != float('inf') else 'inf'
                for x in row
            ) + '\n')

# --- Funzione principale di caricamento e calcolo ---

def load_fingerprint_and_compute(folder_path, matrices_output_base_folder):
    """
    Carica una singola impronta da folder_path, costruisce G,
    calcola (o ricarica da file) M1, M2, M3, M4.
    Ritorna (G, M1, M2, M3, M4).
    """
    # Carica i file JSON
    nodes_file = os.path.join(folder_path, "nodes_graph.json")
    edges_file = os.path.join(folder_path, "edges_graph.json")

    if not os.path.exists(nodes_file) or not os.path.exists(edges_file):
        print(f"Errore: File nodes_graph.json o edges_graph.json non trovati in {folder_path}.")
        return None, None, None, None, None

    # Cartella di output per le matrici specifica per questa impronta
    impronta_nome = os.path.basename(folder_path)
    matrices_folder = os.path.join(matrices_output_base_folder, impronta_nome)

    m1_path = os.path.join(matrices_folder, "M1.csv")
    m2_path = os.path.join(matrices_folder, "M2.csv")
    m3_path = os.path.join(matrices_folder, "M3.csv")
    m4_path = os.path.join(matrices_folder, "M4.csv")

    # Costruisci comunque il grafo G
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
        if G.has_node(node1) and G.has_node(node2):
             # Assicurati che 'distance' sia un float o None
            if dist is not None:
                try:
                    dist = float(dist)
                except (ValueError, TypeError):
                    print(f"Attenzione: Distanza non valida '{dist}' per arco ({node1}, {node2}). Impostata a None.")
                    dist = None # O gestisci diversamente
            G.add_edge(node1, node2, type=etype, distance=dist)
        else:
            print(f"Attenzione: arco con nodi {edge['nodes']} non valido (uno o entrambi i nodi non esistono nel grafo). Arco ignorato.")


    # Se le matrici esistono già, le carichiamo
    if (os.path.exists(m1_path) and os.path.exists(m2_path) and
        os.path.exists(m3_path) and os.path.exists(m4_path)):
        print(f"\nMatrici già esistenti per {impronta_nome}, caricamento in corso...")
        try:
            M1 = load_matrix_from_file(m1_path)
            M2 = load_matrix_from_file(m2_path)
            M3 = load_matrix_from_file(m3_path)
            M4 = load_matrix_from_file(m4_path)
            print(f"Matrici caricate con successo da: {matrices_folder}")
            return G, M1, M2, M3, M4
        except Exception as e:
            print(f"Errore durante il caricamento delle matrici per {impronta_nome}: {e}. Ricalcolo...")
            # Continua per ricalcolare

    # Altrimenti, le calcoliamo da zero
    print(f"\nCalcolo delle matrici per {impronta_nome}...")
    os.makedirs(matrices_folder, exist_ok=True) # Crea la cartella se non esiste

    # --- Funzioni peso definite localmente (usate solo qui) ---
    def weight_function_m1(u, v, d):
        arco_type = d.get('type')
        if arco_type == 'added':
            return 1.0
        elif arco_type == 'border':
            return 5.0
        else: # 'ridge' o altri tipi considerati "veri"
            return 0.0001 # Costo molto basso per favorire questi archi

    def weight_function_m2(u, v, d):
        # Priorità alla distanza precalcolata sull'arco 'ridge'
        dist_attr = d.get('distance')
        if d.get('type') != 'added' and dist_attr is not None:
             return float(dist_attr) # Usa la distanza dell'arco se esiste e non è 'added'
        else:
            # Altrimenti (arco 'added' o 'ridge' senza distanza) usa euclidea
            try:
                pos_u = G.nodes[u]['pos']
                pos_v = G.nodes[v]['pos']
                return math.dist(pos_u, pos_v)
            except KeyError:
                print(f"Attenzione: Coordinate mancanti per i nodi {u} o {v} nel calcolo M2.")
                return float('inf') # Ritorna infinito se le posizioni non sono disponibili


    N = G.number_of_nodes()
    if N == 0:
        print(f"Errore: Grafo vuoto per {impronta_nome}.")
        return G, [], [], [], [] # Ritorna matrici vuote

    # Inizializza matrici con 'inf'
    M1 = [[float('inf')] * N for _ in range(N)]
    M2 = [[float('inf')] * N for _ in range(N)]
    M3 = [[float('inf')] * N for _ in range(N)]
    M4 = [[float('inf')] * N for _ in range(N)]

    # Imposta la diagonale a 0
    for i in range(N):
        M1[i][i] = 0.0
        M2[i][i] = 0.0
        M3[i][i] = 0.0
        M4[i][i] = 0

    # Calcolo M1
    print("Calcolo M1...")
    for node_start in G.nodes():
        dist_dict = single_source_custom_dijkstra(G, node_start, weight_function_m1)
        for node_end, dist_val in dist_dict.items():
            if 0 <= node_start < N and 0 <= node_end < N:
                 M1[node_start][node_end] = dist_val

    # Calcolo M2
    print("Calcolo M2...")
    for node_start in G.nodes():
        dist_dict = single_source_custom_dijkstra(G, node_start, weight_function_m2)
        for node_end, dist_val in dist_dict.items():
            if 0 <= node_start < N and 0 <= node_end < N:
                M2[node_start][node_end] = dist_val

    # Calcolo M3 (euclidea pura)
    print("Calcolo M3...")
    coords = nx.get_node_attributes(G, 'pos')
    node_list = list(G.nodes()) # Ottieni l'ordine dei nodi come sono nel grafo
    node_indices = {node_id: i for i, node_id in enumerate(node_list)}

    for i_idx, i_node in enumerate(node_list):
        for j_idx, j_node in enumerate(node_list):
             if i_idx == j_idx:
                 M3[i_idx][j_idx] = 0.0
             else:
                 try:
                    pos_i = coords[i_node]
                    pos_j = coords[j_node]
                    M3[i_idx][j_idx] = math.dist(pos_i, pos_j)
                 except KeyError:
                     print(f"Attenzione: Coordinate mancanti per nodi {i_node} o {j_node} in M3.")
                     M3[i_idx][j_idx] = float('inf') # O gestisci diversamente

    # Calcolo M4 (numero di salti, BFS) - Solo su archi non 'added'
    print("Calcolo M4...")
    # Crea un grafo temporaneo senza archi 'added' per BFS
    G_no_added = G.copy()
    added_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('type') == 'added']
    G_no_added.remove_edges_from(added_edges)

    for node_start in G_no_added.nodes():
         # Esegui BFS sul grafo senza archi 'added'
        dist_dict = nx.single_source_shortest_path_length(G_no_added, node_start)
        idx_start = node_indices.get(node_start)
        if idx_start is not None:
            for node_end, dist_val in dist_dict.items():
                 idx_end = node_indices.get(node_end)
                 if idx_end is not None:
                     M4[idx_start][idx_end] = dist_val


    # Salviamo le matrici calcolate
    try:
        save_matrix_to_file(M1, m1_path)
        save_matrix_to_file(M2, m2_path)
        save_matrix_to_file(M3, m3_path)
        save_matrix_to_file(M4, m4_path)
        print(f"M1, M2, M3, M4 salvate in: {matrices_folder}")
    except Exception as e:
        print(f"Errore durante il salvataggio delle matrici per {impronta_nome}: {e}")

    return G, M1, M2, M3, M4