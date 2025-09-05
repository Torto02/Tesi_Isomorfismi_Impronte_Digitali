# graph_processing.py
import os
import json
import networkx as nx
import math

# --- Funzioni Helper per Calcolo Matrici ---

def single_source_shortest_paths_and_costs(graph, source, weight_func):
    """
    Esegue Dijkstra sul 'graph' a partire da 'source' usando 'weight_func'.
    Applica pesi temporanei agli archi per usare nx.single_source_dijkstra.

    Ritorna:
        tuple: (dict_distanze, dict_percorsi)
               dict_distanze: {nodo_destinazione: costo_minimo}
               dict_percorsi: {nodo_destinazione: lista_nodi_nel_percorso}
               Restituisce dizionari vuoti o solo con source se ci sono problemi.
    """
    # Verifica se il nodo sorgente esiste nel grafo
    if source not in graph:
        print(f"Errore: Nodo sorgente {source} non trovato nel grafo.")
        return {source: 0.0}, {source: [source]} # Ritorna valori minimi

    # Applica pesi temporanei agli archi
    # È importante gestire archi che potrebbero non avere tutti gli attributi
    for u, v, d in graph.edges(data=True):
        # Assicurati che d sia un dizionario, altrimenti inizializzalo
        if not isinstance(d, dict):
            graph.edges[u, v]['temp_weight'] = float('inf') # Assegna un peso infinito se dati mancanti
            continue
        try:
             # Calcola il peso usando la funzione fornita
             d['temp_weight'] = weight_func(u, v, d)
        except Exception as e:
             print(f"Errore nel calcolare peso per arco ({u},{v}): {e}. Impostato a infinito.")
             d['temp_weight'] = float('inf') # Peso infinito in caso di errore nella funzione peso


    distances = {}
    paths = {}
    try:
        # Usa nx.single_source_dijkstra che ritorna distanze e percorsi
        # Il parametro target=None fa sì che calcoli per tutti i nodi raggiungibili
        distances, paths = nx.single_source_dijkstra(graph, source, weight='temp_weight')

    except nx.NetworkXNoPath:
        # Caso in cui non ci sono percorsi dal nodo source (es. isolato o disconnesso)
        distances = {source: 0.0}
        paths = {source: [source]} # Percorso solo per il nodo stesso
        # Non è un errore critico, ma segnala la situazione
        # print(f"Attenzione: Nessun percorso trovato da nodo {source} in single_source_shortest_paths_and_costs.")
    except Exception as e:
         # Gestisce altri errori potenziali di NetworkX o della funzione peso
         print(f"Errore durante l'esecuzione di Dijkstra da {source}: {e}")
         # Ritorna comunque valori minimi per permettere al programma di continuare se possibile
         distances = {source: 0.0}
         paths = {source: [source]}


    # Ripulisce la chiave 'temp_weight' dagli archi
    for u, v, d in graph.edges(data=True):
         # Verifica se la chiave esiste prima di eliminarla
         if isinstance(d, dict) and 'temp_weight' in d:
             del d['temp_weight']

    return distances, paths

def count_intermediate_added_nodes(graph, path):
    """
    Conta i nodi con type='added' in un percorso, ESCLUDENDO il primo e l'ultimo nodo.
    Ritorna 0 se il percorso è vuoto o ha meno di 3 nodi.
    """
    count = 0
    if not path or len(path) < 3: # Servono almeno 3 nodi per avere un intermedio
        return 0
    # Itera sui nodi INTERMEDI (dal secondo al penultimo)
    for node_id in path[1:-1]:
        try:
            # Verifica se il nodo esiste e se ha il tipo 'added'
            if graph.has_node(node_id) and graph.nodes[node_id].get('type') == 'added':
                count += 1
        except KeyError:
             pass
        except Exception as e:
             print(f"Errore nel controllare il tipo del nodo {node_id} nel percorso: {e}")
             pass # Ignora il nodo in caso di errore
    return count

def load_matrix_from_file(file_path):
    """Carica una matrice da un file CSV."""
    matrix = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                # Gestisce correttamente 'inf' e converte gli altri in float
                row = [float(val) if val.strip().lower() != 'inf' else float('inf') for val in line.strip().split(',')]
                matrix.append(row)
    except FileNotFoundError:
        print(f"Attenzione: File matrice non trovato: {file_path}. Sarà ricalcolato.")
        return None # Ritorna None se il file non esiste
    except Exception as e:
        print(f"Errore durante la lettura della matrice {file_path}: {e}. Sarà ricalcolato.")
        return None # Ritorna None in caso di altri errori di lettura
    return matrix

def save_matrix_to_file(matrix, filename):
    """Salva una matrice (lista di liste) su file CSV, gestendo 'inf'."""
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w') as f:
            for row in matrix:
                # Converte inf in stringa 'inf', altri numeri in stringa standard
                f.write(','.join( str(x) if x != float('inf') else 'inf' for x in row ) + '\n')
    except Exception as e:
        print(f"Errore durante il salvataggio della matrice {filename}: {e}")


# --- Funzione principale di caricamento e calcolo ---

def load_fingerprint_and_compute(folder_path, matrices_output_base_folder):
    """
    Carica una singola impronta da folder_path, costruisce G, calcola (o ricarica)
    M_scavalcamenti (conta 'added' nei percorsi), M3 (euclidea).
    M1 matrix computation has been removed as it's no longer used.

    Ritorna:
        tuple: (G, None, M_scavalcamenti, M3) o (None, None, None, None) in caso di errore critico.
    """
    #! 1) Carica i file JSON
    nodes_file = os.path.join(folder_path, "nodes_graph.json")
    edges_file = os.path.join(folder_path, "edges_graph.json")

    if not os.path.exists(nodes_file) or not os.path.exists(edges_file):
        print(f"Errore: File nodes_graph.json o edges_graph.json non trovati in {folder_path}.")
        return None, None, None, None

    # Cartella di output per le matrici specifica per questa impronta
    impronta_nome = os.path.basename(folder_path)
    matrices_folder = os.path.join(matrices_output_base_folder, impronta_nome)

    # Definisci i percorsi per le matrici necessarie
    m_scavalcamenti_path = os.path.join(matrices_folder, "M_scavalcamenti.csv") # Nuovo nome
    m3_path = os.path.join(matrices_folder, "M3.csv")
    # m1_path, m2_path e m4_path rimossi

    #! 2) --- Costruzione Grafo G ---
    G = nx.Graph()
    node_map = {} # Mappa da ID originale a indice interno (0..N-1) se necessario
    node_list_for_matrix = [] # Lista ordinata dei nodi per coerenza con le matrici

    try:
        with open(nodes_file, 'r') as f:
            nodes_data = json.load(f)
        with open(edges_file, 'r') as f:
            edges_data = json.load(f)

        nodes = nodes_data['nodes']
        edges = edges_data['edges']

        # Aggiungi nodi e costruisci mappa/lista
        for i, node in enumerate(nodes):
            # Assumiamo che l'ID del nodo sia l'indice 'i' se non specificato diversamente
            node_id = node.get('id', i) # Usa 'id' se presente, altrimenti l'indice
            coord = tuple(node.get('coordinates', [0, 0]))
            ntype = node.get('type', 'unknown')
            G.add_node(node_id, pos=coord, type=ntype)
            node_map[node_id] = i # Mappa l'ID del nodo all'indice della matrice
            node_list_for_matrix.append(node_id) # Mantieni l'ordine

        N = len(node_list_for_matrix) # Numero totale di nodi

        # Aggiungi archi
        for edge in edges:
            # Assicurati che i nodi nell'arco esistano nel grafo
            node1, node2 = edge['nodes']
            if node1 in G and node2 in G:
                etype = edge.get('type', 'edge')
                dist = edge.get('distance', None)
                # Assicurati che 'distance' sia un float o None
                if dist is not None:
                    try:
                        dist = float(dist)
                    except (ValueError, TypeError):
                        print(f"Attenzione: Distanza non valida '{dist}' per arco ({node1}, {node2}). Impostata a None.")
                        dist = None
                G.add_edge(node1, node2, type=etype, distance=dist)
            else:
                print(f"Attenzione: arco con nodi {edge['nodes']} non valido (uno o entrambi i nodi non esistono nel grafo). Arco ignorato.")

    except Exception as e:
        print(f"Errore critico durante la costruzione del grafo da {folder_path}: {e}")
        return None, None, None, None

    if N == 0:
        print(f"Errore: Grafo vuoto per {impronta_nome}.")
        return G, None, [], [] # Ritorna None per M1, matrici vuote per il resto se il grafo è vuoto

    #! 3) --- Caricamento o Calcolo Matrici ---

    # Prova a caricare le matrici esistenti
    M_scavalcamenti = load_matrix_from_file(m_scavalcamenti_path)
    M3 = load_matrix_from_file(m3_path)

    #! 4.A) Verifica se tutte le matrici necessarie sono state caricate con successo
    if M_scavalcamenti is not None and M3 is not None:
         valid_dims = (len(M_scavalcamenti) == N and len(M_scavalcamenti[0]) == N and
                       len(M3) == N and len(M3[0]) == N)
         if valid_dims:
             print(f"\nMatrici M_scavalcamenti, M3 già esistenti e valide per {impronta_nome}, caricamento completato.")
             return G, None, M_scavalcamenti, M3
         else:
             print(f"\nDimensioni matrici caricate non valide per {impronta_nome}. Ricalcolo...")
             M_scavalcamenti, M3 = None, None 
    else:
        print(f"\nUna o più matrici non trovate o non valide per {impronta_nome}. Ricalcolo...")

    #! 4.B) --- Calcolo Matrici (se non caricate) ---
    print(f"\nInizio calcolo matrici per {impronta_nome}...")
    os.makedirs(matrices_folder, exist_ok=True) # Crea la cartella se non esiste

    # Funzione peso per calcolare i percorsi più brevi per M_scavalcamenti
    def weight_function_shortest_path(u, v, d):
        # d è il dizionario attributi dell'arco G[u][v]
        arco_type = d.get('type') if isinstance(d, dict) else 'unknown'
        if arco_type == 'added':
            return 1.0
        elif arco_type == 'border':
            return 5.0
        elif arco_type == 'ridge': # Tipo 'ridge' o altri considerati "reali"
            return 0.0001 # Costo molto basso per favorire questi archi
        else: # Tipi sconosciuti o archi senza attributi
             # print(f"Attenzione: Tipo arco non gestito o dati mancanti per ({u},{v}). Tipo: {arco_type}. Assegnato peso alto.")
             return 1000.0 # Assegna un costo alto per penalizzare


    #! 4.B.1) Inizializza matrici con valori di default
    if M_scavalcamenti is None:
        M_scavalcamenti = [[float('inf')] * N for _ in range(N)]
        for i in range(N): M_scavalcamenti[i][i] = 0 # Scavalcamenti su se stesso è 0
    if M3 is None:
        M3 = [[float('inf')] * N for _ in range(N)]
        for i in range(N): M3[i][i] = 0.0

    #! 4.B.2) Calcolo M_scavalcamenti (usando Dijkstra per trovare percorsi più brevi)
    print("Calcolo M_scavalcamenti (conta 'added' sui percorsi più brevi)...")
    # Itera usando gli ID dei nodi presenti nel grafo
    for node_start_id in node_list_for_matrix:
        distances, paths = single_source_shortest_paths_and_costs(G, node_start_id, weight_function_shortest_path)

        # Ottieni l'indice della matrice per il nodo di partenza
        idx_start = node_map.get(node_start_id)
        if idx_start is None: continue

        # Popola M_scavalcamenti per tutte le destinazioni raggiunte
        for node_end_id, dist_val in distances.items():
            idx_end = node_map.get(node_end_id)
            if idx_end is None: continue # Salta se l'ID destinazione non ha indice

            #! Popolamento di M_scavalcamenti
            current_path = paths.get(node_end_id) # Ottieni il percorso corrispondente
            if current_path:
                added_node_count = count_intermediate_added_nodes(G, current_path)
                M_scavalcamenti[idx_start][idx_end] = added_node_count
            else:
                # Se non c'è percorso, mettiamo inf per scavalcamenti
                 M_scavalcamenti[idx_start][idx_end] = float('inf')


    #! 4.B.3) Calcolo M3 (euclidea pura)
    if M3[0][1] == float('inf'): # Controlla se M3 è stata inizializzata ma non calcolata
        print("Calcolo M3 (distanza euclidea)...")
        coords = nx.get_node_attributes(G, 'pos')
        # Usa node_list_for_matrix per iterare nell'ordine corretto
        for i_idx, i_node_id in enumerate(node_list_for_matrix):
            for j_idx, j_node_id in enumerate(node_list_for_matrix):
                if i_idx == j_idx:
                    M3[i_idx][j_idx] = 0.0
                else:
                    try:
                        pos_i = coords[i_node_id]
                        pos_j = coords[j_node_id]
                        M3[i_idx][j_idx] = math.dist(pos_i, pos_j)
                    except KeyError:
                        print(f"Attenzione: Coordinate mancanti per nodi {i_node_id} o {j_node_id} in M3.")
                        M3[i_idx][j_idx] = float('inf') # O gestisci diversamente


    # --- Salvataggio Matrici Calcolate ---
    print("Salvataggio matrici calcolate...")
    save_matrix_to_file(M_scavalcamenti, m_scavalcamenti_path)
    save_matrix_to_file(M3, m3_path)
    print(f"M_scavalcamenti, M3 salvate in: {matrices_folder}")

    # Ritorna il grafo e le matrici calcolate/caricate (M1 is None since it's no longer computed)
    return G, None, M_scavalcamenti, M3

