

#!/usr/bin/env python3
import os
import math
import networkx as nx
import datetime
import time
import pickle
import hashlib
from multiprocessing import get_context, cpu_count

# Importa funzioni dai moduli creati
from graph_processing import load_fingerprint_and_compute
from subgraph_operations import (
    get_subgraph_within_radius,
    get_connected_subgraphs_of_minutiae_parallel
)
from matching import match_subgraph
from plotting import (
    plot_and_save_subgraph,
    plot_mapping,
    plot_final_graphs,
    plot_match_with_context#,
    # plot_chirality_check
)
from stats_logger import StatsLogger

# --- Costanti globali ---
BASE_FOLDER_IMPRONTE           = "/Users/riccardotortorelli/Desktop/Tesi/Archivio/"
OUTPUT_FOLDER_MATRICES         = "/Users/riccardotortorelli/Desktop/Tesi/OutputMatrices"
CACHE_FOLDER                   = "/Users/riccardotortorelli/Desktop/Tesi/FingerPrintCache"

RADIUS_PERCENTAGE_A            = 0.1
RADIUS_PERCENTAGE_B            = 0.1
MINUTIAE_SUBGRAPH_SIZE         = 6
MIN_MATCH_NODES                = 6
MATCHING_COST_THRESHOLD_REL    = 0.3
MATCHING_MAX_RIDGE_DIFF        = 1
MATCHING_ANGLE_TOLERANCE_DEGREES = 20
MATCHING_MAX_EDGE_LENGTH_RATIO = 2.0

# Variabili globali che i worker useranno
_global_subA   = None
_global_subB   = None
_global_params = None

def find_max_finite_distance(matrix):
    max_dist = 0.0
    if not matrix:
        return 100.0
    for row in matrix:
        for val in row or []:
            if isinstance(val, (int, float)) and val != float('inf') and val > max_dist:
                max_dist = val
    return max_dist if max_dist > 0 else 100.0

def find_most_central_minutia(graph, minutiae_nodes):
    """
    Trova la minuzia più centrale basandosi sulla posizione geometrica.
    Calcola il centroide di tutte le minuzie e trova quella più vicina ad esso.
    
    Args:
        graph: Il grafo contenente le posizioni dei nodi
        minutiae_nodes: Lista dei nodi che rappresentano le minuzie
        
    Returns:
        Il nodo della minuzia più centrale
    """
    if not minutiae_nodes:
        return None
    
    # Calcola il centroide di tutte le minuzie
    positions = [graph.nodes[node]['pos'] for node in minutiae_nodes]
    centroid_x = sum(pos[0] for pos in positions) / len(positions)
    centroid_y = sum(pos[1] for pos in positions) / len(positions)
    centroid = (centroid_x, centroid_y)
    
    # Trova la minuzia più vicina al centroide
    min_distance = float('inf')
    most_central_node = None
    
    for node in minutiae_nodes:
        node_pos = graph.nodes[node]['pos']
        distance = math.dist(node_pos, centroid)
        
        if distance < min_distance:
            min_distance = distance
            most_central_node = node
    
    print(f"Centroide calcolato: ({centroid_x:.2f}, {centroid_y:.2f})")
    print(f"Minuzia più centrale: nodo {most_central_node} a distanza {min_distance:.2f} dal centroide")
    
    return most_central_node

def generate_cache_key(fingerprint_name, central_node, radius_percentage, subgraph_size):
    """
    Genera una chiave univoca per la cache basata sui parametri dell'elaborazione.
    """
    key_string = f"{fingerprint_name}_{central_node}_{radius_percentage}_{subgraph_size}"
    return hashlib.md5(key_string.encode()).hexdigest()

def save_to_cache(cache_key, data, cache_folder):
    """
    Salva i dati nella cache.
    
    Args:
        cache_key: Chiave univoca per identificare i dati
        data: Dizionario contenente i dati da salvare
        cache_folder: Cartella dove salvare la cache
    """
    os.makedirs(cache_folder, exist_ok=True)
    cache_file = os.path.join(cache_folder, f"{cache_key}.pkl")
    
    try:
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)
        print(f"Dati salvati nella cache: {cache_file}")
    except Exception as e:
        print(f"Errore nel salvare la cache: {e}")

def load_from_cache(cache_key, cache_folder):
    """
    Carica i dati dalla cache.
    
    Args:
        cache_key: Chiave univoca per identificare i dati
        cache_folder: Cartella dove cercare la cache
        
    Returns:
        Dizionario con i dati salvati o None se non trovati
    """
    cache_file = os.path.join(cache_folder, f"{cache_key}.pkl")
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        with open(cache_file, 'rb') as f:
            data = pickle.load(f)
        print(f"Dati caricati dalla cache: {cache_file}")
        return data
    except Exception as e:
        print(f"Errore nel caricare la cache: {e}")
        return None

def init_worker(subA, subB, params):
    """
    Inizializza subA, subB e params nei processi figli
    per evitare di serializzarli ad ogni chiamata.
    """
    global _global_subA, _global_subB, _global_params
    _global_subA   = subA
    _global_subB   = subB
    _global_params = params

def worker_match_indices(indices):
    """
    Riceve (i,j), estrae i due sottografi da _global_subA/B
    e chiama match_subgraph. Restituisce None o (i,j,mapping,score).
    """
    i, j = indices
    subG_A = _global_subA[i][1]
    subG_B = _global_subB[j][1]
    p = _global_params

    # VF2 raffinato con controlli geometrici
    success, mapping, score, _ = match_subgraph(
        subG_A, subG_B,
        p['M3_A'], p['M3_B'],
        p['M_scav_A'], p['M_scav_B'],
        angle_tolerance_degrees=p.get('ang_tol', 30),
        max_edge_length_ratio=p.get('edge_ratio', 3.0)
    )
    if success and score > 0.0:
        return (i, j, mapping, score)
    return None

def main():
    # --- Creo cartelle di output ---
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    OUTPUT_BASE_FOLDER = os.path.join(
        "/Users/riccardotortorelli/Desktop/Tesi/Output",
        f"Run_{timestamp}"
    )
    OUTPUT_FOLDER_GRAPHS        = os.path.join(OUTPUT_BASE_FOLDER, "Graphs")
    OUTPUT_FOLDER_SUBGRAPHS     = os.path.join(OUTPUT_BASE_FOLDER, "Subgraphs")
    OUTPUT_FOLDER_FINAL_GRAPHS  = os.path.join(OUTPUT_BASE_FOLDER, "Final_Graphs")
    output_folder = os.environ.get("OUTPUT_FOLDER", "./output")
    logger_csv_filename = os.environ.get("LOGGER_CSV_FILENAME", "logger.csv")
    logger = StatsLogger(output_folder, csv_filename=logger_csv_filename)
    # for d in (OUTPUT_FOLDER_GRAPHS, OUTPUT_FOLDER_SUBGRAPHS, OUTPUT_FOLDER_FINAL_GRAPHS):
    #     os.makedirs(d, exist_ok=True)

    # --- Controllo cartella impronte ---
    if not os.path.isdir(BASE_FOLDER_IMPRONTE):
        print(f"Errore: '{BASE_FOLDER_IMPRONTE}' non è una cartella valida.")
        return

    # --- Selezione impronte ---
    impronte = sorted([
        d for d in os.listdir(BASE_FOLDER_IMPRONTE)
        if os.path.isdir(os.path.join(BASE_FOLDER_IMPRONTE, d)) and not d.startswith('.')
    ])
    if len(impronte) < 2:
        print("Servono almeno 2 cartelle di impronte.")
        return

    print("\n--- Impronte disponibili ---")
    for idx, nome in enumerate(impronte, start=1):
        print(f"{idx}. {nome}")
    idxA = int(input("Seleziona A (numero): ")) - 1
    idxB = int(input("Seleziona B (numero): ")) - 1
    folder_A = os.path.join(BASE_FOLDER_IMPRONTE, impronte[idxA])
    folder_B = os.path.join(BASE_FOLDER_IMPRONTE, impronte[idxB])

    # --- Caricamento e calcolo matrici ---
    print("Calcolo impronta A …")
    start_time_A = time.time()
    G_A, M1_A, M_scav_A, M3_A = load_fingerprint_and_compute(folder_A, OUTPUT_FOLDER_MATRICES)
    elapsed_A = time.time() - start_time_A
    print(f"Caricata Impronta A: {impronte[idxA]}, Nodi={G_A.number_of_nodes()}, Archi={G_A.number_of_edges()}, Tempo={elapsed_A:.2f}s")
    
    print("Calcolo impronta B …")
    start_time_B = time.time()
    G_B, M1_B, M_scav_B, M3_B = load_fingerprint_and_compute(folder_B, OUTPUT_FOLDER_MATRICES)
    elapsed_B = time.time() - start_time_B
    print(f"Caricata Impronta B: {impronte[idxB]}, Nodi={G_B.number_of_nodes()}, Archi={G_B.number_of_edges()}, Tempo={elapsed_B:.2f}s")

    # --- Selezione automatica della minuzia più centrale per A ---
    minutiaeA = sorted(n for n,d in G_A.nodes(data=True) if d.get('type') in ('ending','bifurcation'))
    print(f"\nTrovate {len(minutiaeA)} minuzie nell'impronta A")
    
    # Selezione automatica della minuzia più centrale
    start_nodeA = find_most_central_minutia(G_A, minutiaeA)
    print(f"Minuzia A selezionata automaticamente: nodo {start_nodeA}")
    
    # --- Verifica cache per impronta A ---
    cache_key = generate_cache_key(impronte[idxA], start_nodeA, RADIUS_PERCENTAGE_A, MINUTIAE_SUBGRAPH_SIZE)
    cached_data = load_from_cache(cache_key, CACHE_FOLDER)
    
    if cached_data is not None:
        print("Dati per impronta A trovati nella cache, caricamento in corso...")
        S_A = cached_data['S_A']
        sub_subgraphs_A = cached_data['sub_subgraphs_A']
        radiusA = cached_data['radiusA']
        print(f"Cache caricata: {len(sub_subgraphs_A)} sottografi per impronta A")
    else:
        print("Cache non trovata per impronta A, calcolo in corso...")
        
        # Calcolo sottografo locale A
        radiusA = RADIUS_PERCENTAGE_A * find_max_finite_distance(M3_A)
        S_A = get_subgraph_within_radius(G_A, M3_A, start_nodeA, radiusA)
        
        # Estrazione sotto-sottografi A
        print("Starting parallel search for subgraphs of size", MINUTIAE_SUBGRAPH_SIZE, "for fingerprint A...")
        t0 = time.time()
        sub_subgraphs_A = get_connected_subgraphs_of_minutiae_parallel(S_A, size=MINUTIAE_SUBGRAPH_SIZE)
        elapsed_subgraphs_A = time.time() - t0
        print(f"A: {len(sub_subgraphs_A)} sottografi trovati in {elapsed_subgraphs_A:.2f}s")
        
        # Salva nella cache
        cache_data = {
            'S_A': S_A,
            'sub_subgraphs_A': sub_subgraphs_A,
            'radiusA': radiusA,
            'fingerprint_name': impronte[idxA],
            'central_node': start_nodeA,
            'radius_percentage': RADIUS_PERCENTAGE_A,
            'subgraph_size': MINUTIAE_SUBGRAPH_SIZE,
            'timestamp': datetime.datetime.now().isoformat()
        }
        save_to_cache(cache_key, cache_data, CACHE_FOLDER)
    
    # Plot sottografo A (sempre necessario per questa esecuzione)
    # plot_and_save_subgraph(
    #     S_A, G_A, start_nodeA,
    #     OUTPUT_FOLDER_GRAPHS,
    #     f"macro_subgraph_A_{impronte[idxA]}_nodo{start_nodeA}.png"
    # )

    # --- Estrazione sottografo locale B (sempre necessario calcolare) ---
    minutiaeB = sorted(n for n,d in G_B.nodes(data=True) if d.get('type') in ('ending','bifurcation'))
    posA = G_A.nodes[start_nodeA]['pos']
    closestB, min_dist = min(
        ((n, math.dist(posA, G_B.nodes[n]['pos'])) for n in minutiaeB),
        key=lambda x: x[1]
    )
    print(f"Minuzia B corrispondente più vicina: nodo {closestB} (distanza: {min_dist:.2f})")
    
    radiusB = RADIUS_PERCENTAGE_B * find_max_finite_distance(M3_B)
    S_B = get_subgraph_within_radius(G_B, M3_B, closestB, radiusB)
    # plot_and_save_subgraph(
    #     S_B, G_B, closestB,
    #     OUTPUT_FOLDER_GRAPHS,
    #     f"macro_subgraph_B_{impronte[idxB]}_nodo{closestB}.png"
    # )

    # --- Estrazione sotto-sottografi B ---
    print("Starting parallel search for subgraphs of size", MINUTIAE_SUBGRAPH_SIZE, "for fingerprint B...")
    t1 = time.time()
    sub_subgraphs_B = get_connected_subgraphs_of_minutiae_parallel(S_B, size=MINUTIAE_SUBGRAPH_SIZE)
    elapsed_subgraphs_B = time.time() - t1
    print(f"B: {len(sub_subgraphs_B)} sottografi trovati in {elapsed_subgraphs_B:.2f}s")

    if not sub_subgraphs_A or not sub_subgraphs_B:
        # Plot finale dei grafi completi con evidenziazione (anche se non ci sono match)
        plot_final_graphs(
        G_A, G_B,
        set(), set(),
        centerA_coords=G_A.nodes[start_nodeA]['pos'],
        radiusA=radiusA,
        centerB_coords=G_B.nodes[closestB]['pos'],
        radiusB=radiusB,
        output_folder=OUTPUT_FOLDER_FINAL_GRAPHS,
        filename=f"final_matches_{impronte[idxA]}_vs_{impronte[idxB]}.png",
        all_matches=[]
        )   

        print("Nessun sotto-sottografo di dimensione richiesta, esco.")
        return

    # --- Preparazione parametri per il matching parallelo ---
    params = {
        'M3_A': M3_A, 'M3_B': M3_B,
        'M_scav_A': M_scav_A, 'M_scav_B': M_scav_B,
        'cost_thr': MATCHING_COST_THRESHOLD_REL,
        'max_ridge': MATCHING_MAX_RIDGE_DIFF,
        'ang_tol': MATCHING_ANGLE_TOLERANCE_DEGREES,
        'edge_ratio': MATCHING_MAX_EDGE_LENGTH_RATIO
    }
    tasks = [(i, j) for i in range(len(sub_subgraphs_A)) for j in range(len(sub_subgraphs_B))]

    # --- Lancio pool fork (macOS) ---
    ctx   = get_context('fork')
    nproc = min(cpu_count(), len(tasks))
    print(f"Matching parallelo su {nproc} processi…")
    with ctx.Pool(processes=nproc, initializer=init_worker, initargs=(sub_subgraphs_A, sub_subgraphs_B, params)) as pool:
        results = pool.imap_unordered(worker_match_indices, tasks, chunksize=500)
        valid = [r for r in results if r]

    # --- Ordino e stampo i match validi ---
    valid.sort(key=lambda x: x[3], reverse=True)
    print(f"Trovati {len(valid)} match validi:")

    # ...existing code...

    def calculate_relation(idA, idB):
        """
        Calcola la relazione di parentela tra due impronte basandosi sul loro codice.
        """
        try:
            familyA, individualA, _, _ = idA.split('_')
            print(f"Family A: {familyA}, Individual A: {individualA}")

            familyB, individualB, _, _ = idB.split('_')
            print(f"Family B: {familyB}, Individual B: {individualB}")
            print(f"Comparing {idA} with {idB}")
            if familyA == familyB:
                if individualA == individualB:
                    return "same_individual"
                elif individualA.startswith("A") and individualB.startswith("C"):
                    return "child_mother"
                elif individualA.startswith("A") and individualB.startswith("B"):
                    return "child_father"
                elif individualA.startswith("A") and (individualB.startswith("G") or individualB.startswith("D") or individualB.startswith("E")):
                    return "siblings"
                elif individualA.startswith("G") and individualB.startswith("G"):
                    return "twins"
                elif individualA.startswith("G") and (individualB.startswith("D") or individualB.startswith("E") or individualB.startswith("A")):
                    return "siblings"
                else:
                    return "same_family"
            else:
                return "stranger"
        except Exception as e:
            print(f"Errore durante il parsing dell'ID: {e}")
            print(f"idA: {idA}, idB: {idB}")
            return "unknown"

    # --- Ordino e stampo i match validi ---
    valid.sort(key=lambda x: x[3], reverse=True)
    print(f"Trovati {len(valid)} match validi:")
# ...existing code...

    relation = calculate_relation(impronte[idxA], impronte[idxB])

    if relation == "unknown":
        print("Relazione tra le impronte non riconosciuta, match scartati.")
    else:
        if not valid:
            # Nessun match trovato
            logger.log(
                idA=impronte[idxA],
                idB=impronte[idxB],
                relation=relation,
                subgraph_id=None,
                nodes_mapped=None,
                score=None
            )
        else:
            for rank, (i, j, mapping, score) in enumerate(valid, start=1):
                print(f"{rank}. A#{i} vs B#{j} → score {score:.4f}")
                subG_A = sub_subgraphs_A[i][1]
                subG_B = sub_subgraphs_B[j][1]

                logger.log(
                    idA=impronte[idxA],
                    idB=impronte[idxB],
                    relation=relation,
                    subgraph_id=f"A{i}_B{j}_rank{rank}",
                    nodes_mapped=len(mapping),
                    score=score,
                    pair_details={
                        "mapping": mapping,
                        "subgraphA_nodes": list(subG_A.nodes),
                        "subgraphB_nodes": list(subG_B.nodes)
                    }
                )

# ...existing code...


    for rank, (i, j, mapping, score) in enumerate(valid, start=1):
        print(f"{rank}. A#{i} vs B#{j} → score {score:.4f}")

    # # --- Plot dei match --- 
    # for rank, (i, j, mapping, score) in enumerate(valid, start=1):
    #     subG_A = sub_subgraphs_A[i][1]
    #     subG_B = sub_subgraphs_B[j][1]

    #     logger.log(
    #         idA=impronte[idxA],
    #         idB=impronte[idxB],
    #         relation="unknown",  # oppure da un dizionario, se hai pairs_metadata
    #         subgraph_id=f"A{i}_B{j}_rank{rank}",
    #         nodes_mapped=len(mapping),
    #         score=score,
    #         pair_details={
    #             "mapping": mapping,
    #             "subgraphA_nodes": list(subG_A.nodes),
    #             "subgraphB_nodes": list(subG_B.nodes)
    #         }
    #     )


    #     plot_mapping(
    #         subG_A, subG_B,
    #         G_A, G_B,
    #         mapping,
    #         OUTPUT_FOLDER_SUBGRAPHS,
    #         f"match_{rank}_score_{score:.4f}_A({len(mapping)})_"
    #         f"{sub_subgraphs_A[i][0]}_vs_B({len(mapping)})_{sub_subgraphs_B[j][0]}.png"
    #     )

    #     plot_match_with_context(
    #         S_A, S_B,
    #         subG_A, subG_B,
    #         G_A, G_B,
    #         mapping,
    #         OUTPUT_FOLDER_SUBGRAPHS,
    #         f"match_{rank}_WITH_CONTEXT.png",
    #         score=score
    #     )

    #     # plot_chirality_check(
    #     #     subG_A, subG_B,
    #     #     mapping,
    #     #     OUTPUT_FOLDER_SUBGRAPHS,
    #     #     f"match_{rank}_CHIRALITY_CHECK.png",
    #     #     score=score
    #     # )

    # # --- Plot finale dei grafi completi con evidenziazione ---
    # all_nodes_A = set().union(*(m[2].keys() for m in valid))
    # all_nodes_B = set().union(*(m[2].values() for m in valid))
    # plot_final_graphs(
    #     G_A, G_B,
    #     all_nodes_A, all_nodes_B,
    #     centerA_coords=G_A.nodes[start_nodeA]['pos'],
    #     radiusA=radiusA,
    #     centerB_coords=G_B.nodes[closestB]['pos'],
    #     radiusB=radiusB,
    #     output_folder=OUTPUT_FOLDER_FINAL_GRAPHS,
    #     filename=f"final_matches_{impronte[idxA]}_vs_{impronte[idxB]}.png",
    #     all_matches=[{'mapping':m[2], 'score':m[3]} for m in valid]
    # )

    print("\nElaborazione completata.")
    if cached_data is None:
        print(f"I dati per l'impronta A sono stati salvati nella cache con chiave: {cache_key}")

if __name__ == '__main__':
    main()