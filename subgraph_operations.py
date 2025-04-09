import networkx as nx

def get_subgraph_within_radius(G, M3, source_node, radius):
    """
    Ritorna il sottografo di G contenente i nodi che distano <= radius dal source_node
    in base alla matrice M3 (che contiene le distanze euclidee).

    Attenzione: Assicura che gli indici usati per M3 corrispondano all'ordine dei nodi in G.
    Se G può avere nodi non sequenziali (es. dopo rimozioni), è necessaria una mappa indici <-> nodi.
    Qui assumiamo che i nodi in G siano 0...N-1 e corrispondano agli indici di M3.
    """
    N = G.number_of_nodes()
    source_node_index = -1 

    # Trova l'indice corretto per source_node in M3
    if G.has_node(source_node):
        try:
            if source_node < N and list(G.nodes())[source_node] == source_node:
                 source_node_index = source_node
            else: 
                 node_list = list(G.nodes())
                 source_node_index = node_list.index(source_node)
        except (ValueError, IndexError):
             print(f"Errore: Impossibile trovare l'indice per source_node {source_node} nel grafo G.")
             return G.subgraph([]).copy() 
    else:
        print(f"Errore: source_node {source_node} non esiste nel grafo G.")
        return G.subgraph([]).copy() 

    if source_node_index == -1 or not M3 or source_node_index >= len(M3):
         print(f"Errore: M3 non valida o indice source_node {source_node_index} fuori dai limiti per M3.")
         return G.subgraph([]).copy()

    try:
        row_distances = M3[source_node_index]
        num_cols = len(row_distances)
        sub_nodes_indices = [j for j in range(num_cols) if row_distances[j] <= radius]
    except IndexError:
         print(f"Errore: Indice source_node {source_node_index} fuori dai limiti per le righe di M3.")
         return G.subgraph([]).copy()


    node_list = list(G.nodes()) 
    sub_nodes = [node_list[j] for j in sub_nodes_indices if j < len(node_list)]

    S = G.subgraph(sub_nodes).copy()
    return S


def get_connected_subgraphs_of_minutiae(S, size=6):
    """
    Genera tutti i sottografi connessi di S composti esclusivamente da 'size' minuzie 'vere',
    escludendo dal calcolo della connettività gli archi di tipo 'added', usando un approccio
    di espansione ricorsiva.
    Ritorna una lista di tuple (tuple_di_nodi_ordinati, sottografo_indotto_da_S).
    """
    # Estrae i nodi minuzia da S
    real_minutiae_nodes = {n for n, data in S.nodes(data=True)
                           if data.get('type') in ('ending', 'bifurcation')}

    if not real_minutiae_nodes:
        return []

    # Crea un grafo temporaneo contenente solo le minuzie e gli archi REALI
    # Questo grafo serve per trovare i vicini durante l'espansione
    S_minutiae_real_edges = nx.Graph()
    S_minutiae_real_edges.add_nodes_from(real_minutiae_nodes)
    for u, v, data in S.edges(data=True):
        if u in real_minutiae_nodes and v in real_minutiae_nodes and data.get('type') != 'added':
            S_minutiae_real_edges.add_edge(u, v)

    # Set per memorizzare i set di nodi trovati 
    risultati_sets = set()

    # Funzione ricorsiva per l'espansione
    def expand(current_nodes_set, candidates_set):
        # Condizione di terminazione: raggiunto la dimensione desiderata
        if len(current_nodes_set) == size:
            risultati_sets.add(frozenset(current_nodes_set))
            return
        if not candidates_set:
             return

        # Prova ad aggiungere un candidato alla volta
        for node_to_add in list(candidates_set):
            new_current_set = current_nodes_set | {node_to_add}


            remaining_candidates = candidates_set - {node_to_add}
            # Trova i vicini reali del nodo aggiunto
            neighbors_of_added = set(S_minutiae_real_edges.neighbors(node_to_add))
            # Aggiungi solo i vicini che non sono già nel gruppo corrente
            new_potential_candidates = neighbors_of_added - new_current_set

            # Unisci i candidati rimanenti con i nuovi potenziali candidati
            next_candidates = remaining_candidates | new_potential_candidates

            # Chiamata ricorsiva
            expand(new_current_set, next_candidates)


    # Avvia l'espansione da ogni minuzia come punto di partenza
    processed_starts = set() # Per ottimizzare se un nodo fa già parte di un risultato
    for start_node in real_minutiae_nodes:
         initial_candidates = set(S_minutiae_real_edges.neighbors(start_node))
         expand({start_node}, initial_candidates)

    final_subgraphs = []
    for node_set in risultati_sets:
        nodes_tuple_sorted = tuple(sorted(list(node_set)))
        # Induci il sottografo finale da S originale per mantenere tutti gli attributi/archi
        subgraph_induced = S.subgraph(node_set).copy()
        final_subgraphs.append((nodes_tuple_sorted, subgraph_induced))

    return final_subgraphs
