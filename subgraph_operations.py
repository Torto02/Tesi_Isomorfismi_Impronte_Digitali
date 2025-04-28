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
    source_node_index = -1 # Inizializza a valore non valido

    # Trova l'indice corretto per source_node in M3
    if G.has_node(source_node):
        try:
            # Prova ad usare il nodo direttamente come indice (se i nodi sono 0..N-1)
            if source_node < N and list(G.nodes())[source_node] == source_node:
                 source_node_index = source_node
            else: # Altrimenti, cerca l'indice nella lista dei nodi
                 node_list = list(G.nodes())
                 source_node_index = node_list.index(source_node)
        except (ValueError, IndexError):
             print(f"Errore: Impossibile trovare l'indice per source_node {source_node} nel grafo G.")
             return G.subgraph([]).copy() # Ritorna grafo vuoto
    else:
        print(f"Errore: source_node {source_node} non esiste nel grafo G.")
        return G.subgraph([]).copy() # Ritorna grafo vuoto

    # Verifica validità indice e M3
    if source_node_index == -1 or not M3 or source_node_index >= len(M3):
         print(f"Errore: M3 non valida o indice source_node {source_node_index} fuori dai limiti per M3.")
         return G.subgraph([]).copy()

    # Estrai i nodi nel raggio basandoti sull'indice corretto
    try:
        row_distances = M3[source_node_index]
        num_cols = len(row_distances)
        sub_nodes_indices = [j for j in range(num_cols) if row_distances[j] <= radius]
    except IndexError:
         print(f"Errore: Indice source_node {source_node_index} fuori dai limiti per le righe di M3.")
         return G.subgraph([]).copy()


    # Mappa gli indici indietro ai node_id originali di G
    node_list = list(G.nodes()) # Assumiamo che l'ordine di M3 corrisponda a questo
    sub_nodes = [node_list[j] for j in sub_nodes_indices if j < len(node_list)] # Filtra indici validi


    # Crea il sottografo indotto da questi nodi
    S = G.subgraph(sub_nodes).copy()
    return S


def get_connected_subgraphs_of_minutiae(S, size=6):
    """
    Genera tutti i sottografi connessi di S contenenti ESATTAMENTE 'size' nodi reali,
    eventualmente arricchiti con nodi 'added' solo se servono da intermediari
    (scavalcamento), ma li esclude dal conteggio size.
    """
    def is_added(n):
        return S.nodes[n].get('type') == 'added'

    # 1) Come prima: estraiamo tutti i sottografi su archi REALI 
    all_nodes = set(S.nodes())
    if not all_nodes:
        return []

    # Ricostruiamo un grafo con soli archi type != 'added'
    S_real = nx.Graph()
    S_real.add_nodes_from(all_nodes)
    for u, v, d in S.edges(data=True):
        if d.get('type') != 'added':
            S_real.add_edge(u, v)

    risultati_sets = set()

    def count_real(ns):
        return sum(1 for x in ns if not is_added(x))

    def expand(curr, cands):
        r = count_real(curr)
        if r == size:
            risultati_sets.add(frozenset(curr))
            return
        if r > size or not cands:
            return

        for n in list(cands):
            # non superare il numero di reali
            if not is_added(n) and r + 1 > size:
                continue
            new_curr = curr | {n}
            rem = cands - {n}
            # nuovi candidati: vicini REALI di n in S_real
            new_nei = set(S_real.neighbors(n))
            expand(new_curr, rem | (new_nei - new_curr))

    for start in all_nodes:
        expand({start}, set(S_real.neighbors(start)))

    # 2) Ora filtriamo ogni sottografo togliendo gli 'added' inutili
    final = []
    for node_set in risultati_sets:
        # sottografo indotto completo (inclusi archi added)
        subG = S.subgraph(node_set).copy()
        # costruiamo il sotto‐grafo “reale” per il test di connettività
        sub_real = nx.Graph()
        sub_real.add_nodes_from(node_set)
        for u, v, d in subG.edges(data=True):
            if d.get('type') != 'added':
                sub_real.add_edge(u, v)

        # elenco reali
        real_nodes = [n for n in node_set if not is_added(n)]
        # se meno di 2 reali, non serve aggiungere alcun added
        to_remove = []
        if len(real_nodes) >= 2:
            # proviamo a rimuovere ciascun added: se i reali restano ancora connessi,
            # quell'added non era necessario → lo tolgo
            for v in node_set:
                if is_added(v):
                    # grafetto senza v
                    Gm = sub_real.copy()
                    Gm.remove_node(v)
                    comp = Gm.subgraph(real_nodes)
                    if nx.is_connected(comp):
                        to_remove.append(v)

        # nodo_set filtrato
        kept = set(node_set) - set(to_remove)
        # deve contenere ancora esattamente size reali
        if sum(1 for n in kept if not is_added(n)) == size:
            final_subG = subG.subgraph(kept).copy()
            final.append((tuple(sorted(kept)), final_subG))


        # # Print nodes and edges of first subG containing an added node
        # for nodes, sg in final:
        #     has_added = any(is_added(n) for n in nodes)
        #     if has_added:
        #         print("First subgraph with added node:")
        #         print("Nodes:", list(sg.nodes()))
        #         print("Edges:", list(sg.edges()))
        #         break

    return final



import networkx as nx
from multiprocessing import Pool, cpu_count


def _expand_worker(args):
    """
    Worker function per espansione da un nodo di partenza.
    Riceve una tupla (start, S, S_real, size) e restituisce un set di frozenset
    contenenti i sottografi reali di dimensione `size` partendo da `start`.
    """
    start, S, S_real, size = args
    risultati = set()

    def is_added(n):
        return S.nodes[n].get('type') == 'added'

    def count_real(ns):
        return sum(1 for x in ns if not is_added(x))

    def expand(curr, cands):
        r = count_real(curr)
        if r == size:
            risultati.add(frozenset(curr))
            return
        if r > size or not cands:
            return
        for n in list(cands):
            if not is_added(n) and r + 1 > size:
                continue
            new_curr = curr | {n}
            rem = cands - {n}
            new_nei = set(S_real.neighbors(n))
            expand(new_curr, rem | (new_nei - new_curr))

    expand({start}, set(S_real.neighbors(start)))
    return risultati


def get_connected_subgraphs_of_minutiae_parallel(S, size=6, processes=None):
    """
    Versione parallelizzata di get_connected_subgraphs_of_minutiae.
    Genera tutti i sottografi connessi di S contenenti esattamente `size` nodi reali,
    eventualmente arricchiti con nodi 'added' come intermediari.

    Args:
        S (nx.Graph): grafo con nodi di tipo 'real' o 'added'.
        size (int): numero esatto di nodi reali nel sottografo.
        processes (int, optional): numero di processi da usare (default: numero di CPU).
    Returns:
        List[Tuple[Tuple[int,...], nx.Graph]]: lista di tuple (nodi, sottografo completo).
    """
    all_nodes = set(S.nodes())
    if not all_nodes:
        return []

    # Pre-costruzione del grafo senza archi 'added'
    S_real = nx.Graph()
    S_real.add_nodes_from(all_nodes)
    for u, v, d in S.edges(data=True):
        if d.get('type') != 'added':
            S_real.add_edge(u, v)

    # Parallel map: espansione su ciascun nodo
    procs = processes or cpu_count()
    args = [(start, S, S_real, size) for start in all_nodes]
    with Pool(processes=procs) as pool:
        results = pool.map(_expand_worker, args)

    # Unione e deduplicazione dei risultati
    risultati_sets = set().union(*results)

    # Fase di filtro: rimuovere i nodi 'added' non strettamente necessari
    final = []
    def is_added(n):
        return S.nodes[n].get('type') == 'added'

    for node_set in risultati_sets:
        subG = S.subgraph(node_set).copy()
        # real_nodes effettivi
        real_nodes = [n for n in node_set if not is_added(n)]
        to_remove = []

        # Solo se ci sono almeno due reali ha senso controllare
        if len(real_nodes) >= 2:
            for v in list(node_set):
                if is_added(v):
                    # Rimuovo v dal sottografo completo
                    Gm = subG.copy()
                    Gm.remove_node(v)
                    # Verifico che tutti i real_nodes siano ancora connessi tramite percorsi in Gm
                    # (che include sia real che added residui)
                    reachable = nx.node_connected_component(Gm, real_nodes[0])
                    if set(real_nodes).issubset(reachable):
                        to_remove.append(v)

        # Mantengo solo i nodi non rimossi
        kept = set(node_set) - set(to_remove)
        # Verifico che ci siano ancora esattamente `size` nodi reali
        if sum(1 for n in kept if not is_added(n)) == size:
            final_subG = subG.subgraph(kept).copy()
            final.append((tuple(sorted(kept)), final_subG))

    return final
