import os
import math
import networkx as nx 
from graph_processing import load_fingerprint_and_compute
from subgraph_operations import get_subgraph_within_radius, get_connected_subgraphs_of_minutiae
from matching import match_subgraphs, is_cost_similar, is_ridge_jump_similar, check_transform_is_ok

from plotting import plot_and_save_subgraph, plot_mapping, plot_final_graphs

#! Cartelle di impronte e output
BASE_FOLDER_IMPRONTE = "/Users/riccardotortorelli/Desktop/Tesi/Archivio/"
OUTPUT_FOLDER_MATRICES = "/Users/riccardotortorelli/Desktop/Tesi/OutputMatrices"
OUTPUT_FOLDER_MACRO_GRAPHS = "/Users/riccardotortorelli/Desktop/Tesi/Output_Macro_Graphs"
OUTPUT_FOLDER_SUBGRAPHS = "/Users/riccardotortorelli/Desktop/Tesi/Output_Subgraphs" # Per i plot dei match singoli 
OUTPUT_FOLDER_FINAL_GRAPHS = "/Users/riccardotortorelli/Desktop/Tesi/Output_Final_Graphs"

#! Parametri Configurabili 
RADIUS_PERCENTAGE_A = 0.1  # Percentuale della max distanza euclidea per il raggio in A
RADIUS_PERCENTAGE_B = 0.20  # Percentuale della max distanza euclidea per il raggio in B (più grande?)
MINUTIAE_SUBGRAPH_SIZE = 6  # Dimensione dei sotto-sottografi di minuzie da cercare
MATCHING_COST_THRESHOLD_REL = 0.40 # Soglia differenza relativa per M1, M2 nel matching
MATCHING_MAX_RIDGE_DIFF = 2      

def find_max_finite_distance(matrix):
    """Trova il massimo valore finito in una matrice di distanze."""
    max_dist = 0.0
    for row in matrix:
        for val in row:
            if val != float('inf') and val > max_dist:
                max_dist = val
    return max_dist if max_dist > 0 else 100.0 


def main():
    if not os.path.exists(BASE_FOLDER_IMPRONTE):
        print(f"Errore: La cartella impronte '{BASE_FOLDER_IMPRONTE}' non esiste.")
        return
    if not os.path.isdir(BASE_FOLDER_IMPRONTE):
         print(f"Errore: '{BASE_FOLDER_IMPRONTE}' non è una cartella.")
         return

    #! --- Selezione Impronte ---
    impronte_disponibili = sorted([
        d for d in os.listdir(BASE_FOLDER_IMPRONTE)
        if os.path.isdir(os.path.join(BASE_FOLDER_IMPRONTE, d)) and not d.startswith('.') # Ignora file nascosti
    ])

    if len(impronte_disponibili) < 2:
        print(f"Errore: Servono almeno 2 cartelle di impronte in '{BASE_FOLDER_IMPRONTE}'.")
        return

    print("\n--- Selezione Impronte ---")
    for idx, nome in enumerate(impronte_disponibili):
        print(f"{idx + 1}. {nome}")

    while True:
        try:
            sceltaA_idx = int(input(f"\nSeleziona il numero dell'impronta A (1-{len(impronte_disponibili)}): ")) - 1
            if 0 <= sceltaA_idx < len(impronte_disponibili):
                improntaA_nome = impronte_disponibili[sceltaA_idx]
                folder_A = os.path.join(BASE_FOLDER_IMPRONTE, improntaA_nome)
                print(f"Selezionata A: {improntaA_nome}")
                break
            else:
                print("Selezione non valida.")
        except ValueError:
            print("Errore: inserisci un numero intero.")

    while True:
        try:
            sceltaB_idx = int(input(f"Seleziona il numero dell'impronta B (1-{len(impronte_disponibili)}): ")) - 1
            if 0 <= sceltaB_idx < len(impronte_disponibili):
                 improntaB_nome = impronte_disponibili[sceltaB_idx]
                 folder_B = os.path.join(BASE_FOLDER_IMPRONTE, improntaB_nome)
                 print(f"Selezionata B: {improntaB_nome}")
                 break
            else:
                 print("Selezione non valida.")
        except ValueError:
            print("Errore: inserisci un numero intero.")

    #! --- Caricamento e Calcolo Matrici ---
    print("\n--- Caricamento/Calcolo Dati Impronta A ---")
    G_A, M1_A, M2_A, M3_A, M4_A = load_fingerprint_and_compute(folder_A, OUTPUT_FOLDER_MATRICES)
    if G_A is None or not M1_A or not M2_A or not M3_A or not M4_A:
        print(f"Errore critico nel caricamento/calcolo per l'impronta A: {improntaA_nome}. Interruzione.")
        return
    print(f"Caricata Impronta A: {improntaA_nome}, Nodi={G_A.number_of_nodes()}, Archi={G_A.number_of_edges()}")


    print("\n--- Caricamento/Calcolo Dati Impronta B ---")
    G_B, M1_B, M2_B, M3_B, M4_B = load_fingerprint_and_compute(folder_B, OUTPUT_FOLDER_MATRICES)
    if G_B is None or not M1_B or not M2_B or not M3_B or not M4_B:
        print(f"Errore critico nel caricamento/calcolo per l'impronta B: {improntaB_nome}. Interruzione.")
        return
    print(f"Caricata Impronta B: {improntaB_nome}, Nodi={G_B.number_of_nodes()}, Archi={G_B.number_of_edges()}")


    #! --- Selezione Minuzia di Partenza in A ---
    print("\n--- Selezione Minuzia di Partenza ---")
    minutia_nodesA = sorted([n for n, data in G_A.nodes(data=True) if data.get('type') in ('ending','bifurcation')])
    if not minutia_nodesA:
        print(f"Errore: Nessuna minuzia ('ending' o 'bifurcation') trovata in {improntaA_nome}.")
        return

    print(f"\nMinuzie disponibili in {improntaA_nome}:")
    for idx, node_id in enumerate(minutia_nodesA):
        try:
             node_type = G_A.nodes[node_id]['type']
             node_pos = G_A.nodes[node_id]['pos']
             print(f"{idx + 1}. Nodo {node_id} - Tipo: {node_type}, Pos: {node_pos}")
        except KeyError:
             print(f"{idx + 1}. Nodo {node_id} - Errore: attributi mancanti.")


    while True:
        try:
            minutiaA_idx_sel = int(input(f"\nSeleziona il numero della minuzia per '{improntaA_nome}' (1-{len(minutia_nodesA)}): ")) - 1
            if 0 <= minutiaA_idx_sel < len(minutia_nodesA):
                minuziaA_id = minutia_nodesA[minutiaA_idx_sel]
                print(f"Hai selezionato la minuzia {minuziaA_id} ({G_A.nodes[minuziaA_id]['type']}) in A.")
                break
            else:
                print(f"Selezione non valida. Inserisci un numero tra 1 e {len(minutia_nodesA)}.")
        except ValueError:
            print("Errore: inserisci un numero intero.")
        except KeyError:
             print(f"Errore: Dati mancanti per la minuzia selezionata. Riprova.")


    #! --- Estrazione Sottografo A (basato su raggio) ---
    print("\n--- Estrazione Sottografi Locali ---")
    max_dist_A = find_max_finite_distance(M3_A)
    radiusA = RADIUS_PERCENTAGE_A * max_dist_A
    print(f"Calcolo raggio per S_A: {RADIUS_PERCENTAGE_A:.0%} di {max_dist_A:.2f} = {radiusA:.2f}")
    S_A = get_subgraph_within_radius(G_A, M3_A, minuziaA_id, radiusA)
    print(f"Sottografo S_A (intorno a {minuziaA_id}): Nodi={S_A.number_of_nodes()}, Archi={S_A.number_of_edges()}")

    #! Plot del "macro" sottografo S_A
    plot_and_save_subgraph(
        S_A, G_A, minuziaA_id, OUTPUT_FOLDER_MACRO_GRAPHS,
        f"macro_subgraph_A_{improntaA_nome}_nodo{minuziaA_id}.png"
    )

    #! --- Selezione (Automatica) Minuzia di Partenza in B ---
    minutia_nodesB = sorted([n for n, data in G_B.nodes(data=True) if data.get('type') in ('ending','bifurcation')])
    if not minutia_nodesB:
        print(f"Errore: Nessuna minuzia trovata in {improntaB_nome}.")
        return

    try:
        pos_minuziaA = G_A.nodes[minuziaA_id]['pos']
    except KeyError:
         print(f"Errore: Posizione mancante per la minuzia {minuziaA_id} in A. Impossibile trovare la più vicina in B.")
         return

    closest_minutiaB_id = None
    min_euclidean_dist = float('inf')

    for nodeB_id in minutia_nodesB:
        try:
             pos_nodeB = G_B.nodes[nodeB_id]['pos']
             distance = math.dist(pos_minuziaA, pos_nodeB)
             if distance < min_euclidean_dist:
                 min_euclidean_dist = distance
                 closest_minutiaB_id = nodeB_id
        except KeyError:
             print(f"Attenzione: Posizione mancante per minuzia {nodeB_id} in B. Ignorata.")
             continue # Ignora questa minuzia B se non ha posizione

    if closest_minutiaB_id is None:
        print(f"Errore: Impossibile trovare una minuzia valida in B vicina a {minuziaA_id}.")
        return

    minuziaB_id = closest_minutiaB_id
    print(f"Minuzia più vicina in '{improntaB_nome}' a {minuziaA_id} (pos {pos_minuziaA}):")
    print(f"-> Nodo {minuziaB_id} ({G_B.nodes[minuziaB_id]['type']}), Distanza Euclidea: {min_euclidean_dist:.2f}")

    #! --- Estrazione Sottografo B (basato su raggio) ---
    max_dist_B = find_max_finite_distance(M3_B)
    radiusB = RADIUS_PERCENTAGE_B * max_dist_B
    print(f"Calcolo raggio per S_B: {RADIUS_PERCENTAGE_B:.0%} di {max_dist_B:.2f} = {radiusB:.2f}")
    S_B = get_subgraph_within_radius(G_B, M3_B, minuziaB_id, radiusB)
    print(f"Sottografo S_B (intorno a {minuziaB_id}): Nodi={S_B.number_of_nodes()}, Archi={S_B.number_of_edges()}")

    #! Plot del "macro" sottografo S_B
    plot_and_save_subgraph(
        S_B, G_B, minuziaB_id, OUTPUT_FOLDER_MACRO_GRAPHS,
        f"macro_subgraph_B_{improntaB_nome}_nodo{minuziaB_id}.png"
    )

    #! --- Ricerca e Matching dei Sotto-Sottografi di Minuzie ---
    print(f"\n--- Ricerca Sotto-Sottografi Connessi di {MINUTIAE_SUBGRAPH_SIZE} Minuzie ---")

    sub_subgraphs_A = get_connected_subgraphs_of_minutiae(S_A, size=MINUTIAE_SUBGRAPH_SIZE)
    sub_subgraphs_B = get_connected_subgraphs_of_minutiae(S_B, size=MINUTIAE_SUBGRAPH_SIZE)


    print(f"Trovati {len(sub_subgraphs_A)} sotto-sottografi connessi di {MINUTIAE_SUBGRAPH_SIZE} minuzie in S_A.")
    print(f"Trovati {len(sub_subgraphs_B)} sotto-sottografi connessi di {MINUTIAE_SUBGRAPH_SIZE} minuzie in S_B.")

    if not sub_subgraphs_A or not sub_subgraphs_B:
        print("Nessun sotto-sottografo di minuzie trovato in una o entrambe le impronte. Impossibile eseguire il matching.")
        return

    print(f"\n--- Esecuzione Matching (Soglia Rel={MATCHING_COST_THRESHOLD_REL}, Diff Max Salti={MATCHING_MAX_RIDGE_DIFF}) ---")
    match_counter = 0
    all_matches = [] # Lista per salvare i dettagli dei match (mapping, nodiA, nodiB)
    matched_nodes_A_global = set() # Set di tutti i nodi di A che sono in almeno un match
    matched_nodes_B_global = set() # Set di tutti i nodi di B che sono in almeno un match

    #! Itera su tutte le coppie di sotto-sottografi (uno da A, uno da B)
    for idxA, (subsetA_nodes, subG_A) in enumerate(sub_subgraphs_A):
        for idxB, (subsetB_nodes, subG_B) in enumerate(sub_subgraphs_B):
            if not subG_A or not subG_B: continue # Salta se vuoti

            # Scegli i nodi iniziali (es. il primo di ogni tupla, che è ordinata)
            start_nodeA = subsetA_nodes[0]
            start_nodeB = subsetB_nodes[0]

            # Tenta il matching partendo da questa coppia
            current_mapping = {}
            visited_pairs_match = set() # Reset per ogni tentativo di match
            success = match_subgraphs(
                subG_A, subG_B,        # I grafi specifici da matchare
                M1_A, M2_A, M4_A,      # Matrici globali di A
                M1_B, M2_B, M4_B,      # Matrici globali di B
                start_nodeA, start_nodeB,
                mapping=current_mapping,
                visited_pairs=visited_pairs_match,
                cost_threshold_rel=MATCHING_COST_THRESHOLD_REL,
                max_ridge_diff=MATCHING_MAX_RIDGE_DIFF
            )

            # Verifica se il match è "completo" (tutti i nodi di subG_A sono stati mappati)
            is_complete_match = success and len(current_mapping) == len(subG_A.nodes())

            if is_complete_match:
                #! Prima di "accettare" il match, controlliamo se c'è riflessione o rotazione eccessiva
                if not check_transform_is_ok(G_A, G_B, current_mapping,
                                            max_rotation_deg=20,
                                            allow_reflection=False):
                    print("   -> Scartato: trasformazione speculare o rotazione troppo grande.")
                    continue

                match_counter += 1
                print(f"\nMatch #{match_counter} Trovato e Accettato!")
                ...

                print(f"  Sottografo A (nodi): {subsetA_nodes}")
                print(f"  Sottografo B (nodi): {subsetB_nodes}")
                print(f"  Mapping: {current_mapping}")

                all_matches.append({
                    'map': current_mapping.copy(),
                    'nodes_A': set(subsetA_nodes),
                    'nodes_B': set(subsetB_nodes)
                })

                matched_nodes_A_global.update(current_mapping.keys())
                matched_nodes_B_global.update(current_mapping.values())

                #! Plot del singolo match trovato
                plot_mapping(
                    subG_A, subG_B,
                    G_A, G_B, 
                    current_mapping,
                    OUTPUT_FOLDER_SUBGRAPHS, 
                    f"match_{match_counter}_A{start_nodeA}_B{start_nodeB}.png"
                )

    print(f"\n--- Risultato Matching ---")
    print(f"Totale combinazioni di sotto-sottografi testate: {len(sub_subgraphs_A) * len(sub_subgraphs_B)}")
    print(f"Numero di match completi trovati: {match_counter}")
    print(f"Nodi totali coinvolti in match in A: {len(matched_nodes_A_global)}")
    print(f"Nodi totali coinvolti in match in B: {len(matched_nodes_B_global)}")


    print("\n--- Generazione Plot Finale ---")
    centerA_coords = G_A.nodes[minuziaA_id].get('pos') if minuziaA_id in G_A else None
    centerB_coords = G_B.nodes[minuziaB_id].get('pos') if minuziaB_id in G_B else None

    plot_final_graphs(
        G_A, G_B,
        matched_nodes_A_global, 
        matched_nodes_B_global,
        centerA_coords=centerA_coords,
        radiusA=radiusA,
        centerB_coords=centerB_coords,
        radiusB=radiusB,
        output_folder=OUTPUT_FOLDER_FINAL_GRAPHS,
        filename=f"final_matches_{improntaA_nome}_vs_{improntaB_nome}.png",
        all_matches=all_matches  
    )

    print("\n--- Elaborazione Completata ---")

if __name__ == "__main__":
    main()

