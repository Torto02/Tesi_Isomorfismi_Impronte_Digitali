import os
import math
import networkx as nx
import datetime

# Importa funzioni dai moduli creati
from graph_processing import load_fingerprint_and_compute
from subgraph_operations import get_subgraph_within_radius, get_connected_subgraphs_of_minutiae_parallel
from matching import match_subgraph
from plotting import plot_and_save_subgraph, plot_mapping, plot_final_graphs,plot_match_with_context
import time

# --- Definisci qui le costanti per i percorsi ---
# NOTA: Aggiorna questi percorsi con quelli corretti sul tuo sistema
BASE_FOLDER_IMPRONTE = "/Users/riccardotortorelli/Desktop/Tesi/Archivio/"
OUTPUT_FOLDER_MATRICES = "/Users/riccardotortorelli/Desktop/Tesi/OutputMatrices"
OUTPUT_FOLDER_GRAPHS = "/Users/riccardotortorelli/Desktop/Tesi/Output_Graphs"
OUTPUT_FOLDER_SUBGRAPHS = "/Users/riccardotortorelli/Desktop/Tesi/Output_Subgraphs"
OUTPUT_FOLDER_FINAL_GRAPHS = "/Users/riccardotortorelli/Desktop/Tesi/Output_Final_Graphs"

# --- Parametri Configurabili ---
RADIUS_PERCENTAGE_A = 0.1 # Percentuale della max distanza euclidea per il raggio in A
RADIUS_PERCENTAGE_B = 0.12 # Percentuale della max distanza euclidea per il raggio in B
MINUTIAE_SUBGRAPH_SIZE = 6 # Dimensione dei sotto-sottografi di minuzie da cercare
MIN_MATCH_NODES = 6       # Numero minimo di nodi matchati per considerare un match valido (>=4)
MATCHING_COST_THRESHOLD_REL = 0.3 # Soglia differenza relativa per M1 cost (0.6 = 60% di tolleranza)
MATCHING_MAX_RIDGE_DIFF = 1     # Soglia differenza assoluta per M_scavalcamenti
MATCHING_ANGLE_TOLERANCE_DEGREES = 28 # Soglia tolleranza angolare in gradi (es. +/- 35 gradi)

def find_max_finite_distance(matrix):
    """Trova il massimo valore finito in una matrice di distanze (usato per M3)."""
    max_dist = 0.0
    if not matrix: return 100.0
    for row in matrix:
        if not row: continue
        for val in row:
            if isinstance(val, (int, float)) and val != float('inf') and val > max_dist:
                max_dist = val
    return max_dist if max_dist > 0 else 100.0

def main():
    # --- Crea una cartella di output unica per questa esecuzione (solo per output diversi dalle matrici) ---
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    OUTPUT_BASE_FOLDER = os.path.join("/Users/riccardotortorelli/Desktop/Tesi/Output", f"Run_{timestamp}")
    OUTPUT_FOLDER_GRAPHS = os.path.join(OUTPUT_BASE_FOLDER, "Graphs")
    OUTPUT_FOLDER_SUBGRAPHS = os.path.join(OUTPUT_BASE_FOLDER, "Subgraphs")
    OUTPUT_FOLDER_FINAL_GRAPHS = os.path.join(OUTPUT_BASE_FOLDER, "Final_Graphs")
    os.makedirs(OUTPUT_FOLDER_GRAPHS, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER_SUBGRAPHS, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER_FINAL_GRAPHS, exist_ok=True)

    # Cartella fissa per le matrici (NON nella cartella della singola run)
    OUTPUT_FOLDER_MATRICES = "/Users/riccardotortorelli/Desktop/Tesi/OutputMatrices"

    # Verifica cartella base impronte
    if not os.path.exists(BASE_FOLDER_IMPRONTE):
        print(f"Errore: La cartella impronte '{BASE_FOLDER_IMPRONTE}' non esiste.")
        return
    if not os.path.isdir(BASE_FOLDER_IMPRONTE):
        print(f"Errore: '{BASE_FOLDER_IMPRONTE}' non è una cartella.")
        return

    # --- Selezione Impronte ---
    impronte_disponibili = sorted([
        d for d in os.listdir(BASE_FOLDER_IMPRONTE)
        if os.path.isdir(os.path.join(BASE_FOLDER_IMPRONTE, d)) and not d.startswith('.')
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

    # --- Caricamento e Calcolo Matrici ---
    print("\n--- Caricamento/Calcolo Dati Impronta A ---")
    # La funzione ora ritorna G, M1, M_scavalcamenti, M3
    G_A, M1_A, M_scavalcamenti_A, M3_A = load_fingerprint_and_compute(folder_A, OUTPUT_FOLDER_MATRICES)
    if G_A is None or M1_A is None or M_scavalcamenti_A is None or M3_A is None:
        print(f"Errore critico nel caricamento/calcolo per l'impronta A: {improntaA_nome}. Interruzione.")
        return
    print(f"Caricata Impronta A: {improntaA_nome}, Nodi={G_A.number_of_nodes()}, Archi={G_A.number_of_edges()}")


    print("\n--- Caricamento/Calcolo Dati Impronta B ---")
    G_B, M1_B, M_scavalcamenti_B, M3_B = load_fingerprint_and_compute(folder_B, OUTPUT_FOLDER_MATRICES)
    if G_B is None or M1_B is None or M_scavalcamenti_B is None or M3_B is None:
        print(f"Errore critico nel caricamento/calcolo per l'impronta B: {improntaB_nome}. Interruzione.")
        return
    print(f"Caricata Impronta B: {improntaB_nome}, Nodi={G_B.number_of_nodes()}, Archi={G_B.number_of_edges()}")


    # --- Selezione Minuzia di Partenza in A ---
    print("\n--- Selezione Minuzia di Partenza ---")
    minutia_nodesA = sorted([n for n, data in G_A.nodes(data=True) if data.get('type') in ('ending','bifurcation')])
    if not minutia_nodesA:
        print(f"Errore: Nessuna minuzia ('ending' o 'bifurcation') trovata in {improntaA_nome}.")
        return

    print(f"\nMinuzie disponibili in {improntaA_nome}:")
    for idx, node_id in enumerate(minutia_nodesA):
        try:
             node_data = G_A.nodes[node_id]
             node_type = node_data.get('type', 'N/D')
             node_pos = node_data.get('pos', ('N/D', 'N/D'))
             print(f"{idx + 1}. Nodo {node_id} - Tipo: {node_type}, Pos: {node_pos}")
        except KeyError:
             print(f"{idx + 1}. Nodo {node_id} - Errore: dati nodo non trovati.")

    while True:
        try:
            minutiaA_idx_sel = int(input(f"\nSeleziona il numero della minuzia per '{improntaA_nome}' (1-{len(minutia_nodesA)}): ")) - 1
            if 0 <= minutiaA_idx_sel < len(minutia_nodesA):
                minuziaA_id = minutia_nodesA[minutiaA_idx_sel]
                if minuziaA_id in G_A:
                     print(f"Hai selezionato la minuzia {minuziaA_id} ({G_A.nodes[minuziaA_id].get('type', 'N/D')}) in A.")
                     break
                else:
                     print(f"Errore: Nodo {minuziaA_id} non trovato nel grafo A. Riprova.")
            else:
                print(f"Selezione non valida.")
        except ValueError:
            print("Errore: inserisci un numero intero.")
        except KeyError:
             print(f"Errore: Dati mancanti per la minuzia selezionata. Riprova.")


    #! --- Estrazione Sottografo A (basato su raggio M3) ---
    print("\n--- Estrazione Sottografi Locali ---")
    max_dist_A = find_max_finite_distance(M3_A)
    radiusA = RADIUS_PERCENTAGE_A * max_dist_A
    print(f"Calcolo raggio per S_A: {RADIUS_PERCENTAGE_A:.0%} di {max_dist_A:.2f} = {radiusA:.2f}")
    S_A = get_subgraph_within_radius(G_A, M3_A, minuziaA_id, radiusA)
    if not S_A:
         print(f"Errore o sottografo A vuoto per nodo {minuziaA_id} e raggio {radiusA:.2f}. Interruzione.")
         return
    print(f"Sottografo S_A (intorno a {minuziaA_id}): Nodi={S_A.number_of_nodes()}, Archi={S_A.number_of_edges()}")

    plot_and_save_subgraph(
        S_A, G_A, minuziaA_id, OUTPUT_FOLDER_GRAPHS,
        f"macro_subgraph_A_{improntaA_nome}_nodo{minuziaA_id}.png"
    )

    # --- Selezione (Automatica) Minuzia di Partenza in B ---
    minutia_nodesB = sorted([n for n, data in G_B.nodes(data=True) if data.get('type') in ('ending','bifurcation')])
    if not minutia_nodesB:
        print(f"Errore: Nessuna minuzia trovata in {improntaB_nome}.")
        return

    try:
        if minuziaA_id not in G_A:
             print(f"Errore: Nodo A selezionato {minuziaA_id} non esiste più nel grafo.")
             return
        pos_minuziaA = G_A.nodes[minuziaA_id]['pos']
    except KeyError:
         print(f"Errore: Posizione mancante per la minuzia {minuziaA_id} in A.")
         return

    closest_minutiaB_id = None
    min_euclidean_dist = float('inf')

    for nodeB_id in minutia_nodesB:
        try:
             if nodeB_id not in G_B: continue
             pos_nodeB = G_B.nodes[nodeB_id]['pos']
             distance = math.dist(pos_minuziaA, pos_nodeB)
             if distance < min_euclidean_dist:
                 min_euclidean_dist = distance
                 closest_minutiaB_id = nodeB_id
        except KeyError:
             print(f"Attenzione: Posizione mancante per minuzia {nodeB_id} in B. Ignorata.")
             continue
        except Exception as e:
             print(f"Errore nel calcolare distanza per nodo B {nodeB_id}: {e}")
             continue

    if closest_minutiaB_id is None:
        print(f"Errore: Impossibile trovare una minuzia valida in B vicina a {minuziaA_id}.")
        return

    minuziaB_id = closest_minutiaB_id
    if minuziaB_id not in G_B:
         print(f"Errore: Nodo B selezionato {minuziaB_id} non esiste più nel grafo.")
         return
    print(f"Minuzia più vicina in '{improntaB_nome}' a {minuziaA_id} (pos {pos_minuziaA}):")
    print(f"-> Nodo {minuziaB_id} ({G_B.nodes[minuziaB_id].get('type', 'N/D')}), Distanza Euclidea: {min_euclidean_dist:.2f}")

    # --- Estrazione Sottografo B (basato su raggio M3) ---
    max_dist_B = find_max_finite_distance(M3_B)
    radiusB = RADIUS_PERCENTAGE_B * max_dist_B
    print(f"Calcolo raggio per S_B: {RADIUS_PERCENTAGE_B:.0%} di {max_dist_B:.2f} = {radiusB:.2f}")
    S_B = get_subgraph_within_radius(G_B, M3_B, minuziaB_id, radiusB)
    if not S_B:
         print(f"Errore o sottografo B vuoto per nodo {minuziaB_id} e raggio {radiusB:.2f}. Interruzione.")
         return
    print(f"Sottografo S_B (intorno a {minuziaB_id}): Nodi={S_B.number_of_nodes()}, Archi={S_B.number_of_edges()}")

    plot_and_save_subgraph(
        S_B, G_B, minuziaB_id, OUTPUT_FOLDER_GRAPHS,
        f"macro_subgraph_B_{improntaB_nome}_nodo{minuziaB_id}.png"
    )

    #! --- Ricerca e Matching dei Sotto-Sottografi di Minuzie ---
    print(f"\n--- Ricerca Sotto-Sottografi Connessi di {MINUTIAE_SUBGRAPH_SIZE} Minuzie ---")

    # Calcoliamo il tempo di ricerca dei sotto-sottografi
    print(f"Calcolo dei sotto-sottografi connessi di {MINUTIAE_SUBGRAPH_SIZE} minuzie in S_A e S_B...")

    start_time_A = time.time()
    sub_subgraphs_A = get_connected_subgraphs_of_minutiae_parallel(S_A, size=MINUTIAE_SUBGRAPH_SIZE)
    elapsed_A = time.time() - start_time_A
    print(f"Tempo impiegato per S_A: {elapsed_A:.2f} secondi.")

    start_time_B = time.time()
    sub_subgraphs_B = get_connected_subgraphs_of_minutiae_parallel(S_B, size=MINUTIAE_SUBGRAPH_SIZE)
    elapsed_B = time.time() - start_time_B
    print(f"Tempo impiegato per S_B: {elapsed_B:.2f} secondi.")



    print(f"Trovati {len(sub_subgraphs_A)} sotto-sottografi connessi di {MINUTIAE_SUBGRAPH_SIZE} minuzie in S_A.")
    print(f"Trovati {len(sub_subgraphs_B)} sotto-sottografi connessi di {MINUTIAE_SUBGRAPH_SIZE} minuzie in S_B.")

    # --- Verifica presenza di un sottografo specifico ---------------------------------
    TARGET_NODES_A = {827, 895, 868, 837, 878, 828}
    TARGET_NODES_B = {1310, 1330, 1329, 1336, 1349, 1318}

    has_target_A = any(TARGET_NODES_A.issubset(set(nodes)) for nodes, _ in sub_subgraphs_A)
    has_target_B = any(TARGET_NODES_B.issubset(set(nodes)) for nodes, _ in sub_subgraphs_B)

    print(f"\nVerifica sottografo target in A: {'Trovato' if has_target_A else 'NON trovato'}")
    print(f"Verifica sottografo target in B: {'Trovato' if has_target_B else 'NON trovato'}\n")

   
    if not sub_subgraphs_A or not sub_subgraphs_B:
        print("Nessun sotto-sottografo di minuzie della dimensione richiesta trovato. Impossibile eseguire il matching.")
        plot_final_graphs(
            G_A, G_B, set(), set(),
            G_A.nodes[minuziaA_id].get('pos') if minuziaA_id in G_A else None, radiusA,
            G_B.nodes[minuziaB_id].get('pos') if minuziaB_id in G_B else None, radiusB,
            OUTPUT_FOLDER_FINAL_GRAPHS,
            f"final_NO_MATCHES_{improntaA_nome}_vs_{improntaB_nome}.png",
            all_matches=[]
        )
        return

    print(f"\n--- Esecuzione Matching (M1 Rel={MATCHING_COST_THRESHOLD_REL}, Scaval Abs={MATCHING_MAX_RIDGE_DIFF}, Ang Tol={MATCHING_ANGLE_TOLERANCE_DEGREES}) ---")
    match_counter = 0
    all_matches = []
    matched_nodes_A_global = set()
    matched_nodes_B_global = set()
    
    total_pairs_to_check = len(sub_subgraphs_A) * len(sub_subgraphs_B)
    checked_count = 0

        
    print(f"\n--- Risultato Matching ---")
    print(f"Totale combinazioni di sotto-sottografi testate: {checked_count}")
    print(f"Numero di match validi trovati (>= {MIN_MATCH_NODES} nodi): {match_counter}")
    print(f"Nodi totali coinvolti in match validi in A: {len(matched_nodes_A_global)}")
    print(f"Nodi totali coinvolti in match validi in B: {len(matched_nodes_B_global)}")
    # In main_script.py, sostituisci il ciclo di matching esistente con questo:

    print(f"\n--- Esecuzione Matching (M1 Rel={MATCHING_COST_THRESHOLD_REL}, Scaval Abs={MATCHING_MAX_RIDGE_DIFF}, Ang Tol={MATCHING_ANGLE_TOLERANCE_DEGREES}) ---")
    match_counter = 0
    all_matches = []
    matched_nodes_A_global = set()
    matched_nodes_B_global = set()

    total_pairs_to_check = len(sub_subgraphs_A) * len(sub_subgraphs_B)
    checked_count = 0

    # Teniamo traccia dei mapping già trovati per evitare duplicati
    found_mappings = set()

    for idxA, (nodesA, subG_A) in enumerate(sub_subgraphs_A):
        for idxB, (nodesB, subG_B) in enumerate(sub_subgraphs_B):
            # Esegui il matching tra i due sottografi
            success, mapping, score, pair_details = match_subgraph(
                subG_A, subG_B,
                M3_A, M3_B,
                M_scavalcamenti_A, M_scavalcamenti_B,
                cost_threshold_rel=MATCHING_COST_THRESHOLD_REL,
                max_ridge_diff=MATCHING_MAX_RIDGE_DIFF,
                angle_tolerance_degrees=MATCHING_ANGLE_TOLERANCE_DEGREES
            )

            checked_count += 1
            if checked_count > 0 and checked_count % 100000 == 0: # Aggiornamento meno frequente
                print(f"  Controllata coppia {checked_count}/{total_pairs_to_check}...")
            
            if not success or score == 0.0:
                continue
                
            # Converti il mapping in una rappresentazione immutabile per il controllo dei duplicati
            mapping_tuple = tuple(sorted((a, b) for a, b in mapping.items()))
            
            # Salta se questo mapping è già stato trovato
            if mapping_tuple in found_mappings:
                continue
                
            # Aggiungi il mapping alla lista dei trovati
            found_mappings.add(mapping_tuple)

            match_counter += 1
            matched_nodesA = list(mapping.keys())
            matched_nodesB = [mapping[n] for n in matched_nodesA]
            
            # Aggiorna i set globali di nodi matchati
            matched_nodes_A_global.update(matched_nodesA)
            matched_nodes_B_global.update(matched_nodesB)

            # Crea un risultato con lo score
            match_result = {
                'id': match_counter,
                'mapping': mapping,
                'nodes_A': matched_nodesA,
                'nodes_B': matched_nodesB,
                'score': score,
                'pair_details': pair_details,
                'subG_A': subG_A,
                'subG_B': subG_B,
                'start_nodeA': nodesA[0],
                'start_nodeB': nodesB[0]
            }
            
            all_matches.append(match_result)

            # Stampa informazioni sul match
            print(f"\nMatch #{match_counter} Trovato! Score: {score:.4f}")
            print(f"  Sottografo A (nodi {matched_nodesA}):")
            print(f"  Sottografo B (nodi {matched_nodesB}):")
            print(f"  Mapping: {mapping}")

    # Ordina i match per score (dal migliore al peggiore)
    all_matches.sort(key=lambda x: x['score'], reverse=True)

    # Stampare i risultati ordinati
    print(f"\n--- Graduatoria dei {len(all_matches)} Match Trovati ---")
    for i, match in enumerate(all_matches):
        print(f"{i+1}. Match #{match['id']} - Score: {match['score']:.4f} - Nodi A: {match['nodes_A']}, Nodi B: {match['nodes_B']}")

    # Poi procedi con il plotting come prima, ma usa all_matches ordinato
    for match in all_matches:
        # Chiama la funzione di plot
        plot_mapping(
            match['subG_A'], match['subG_B'],
            G_A, G_B,
            match['mapping'],
            OUTPUT_FOLDER_SUBGRAPHS,
            f"match_{match['id']}_score_{match['score']:.4f}_A({len(match['nodes_A'])}of{MINUTIAE_SUBGRAPH_SIZE})_"
            f"{match['start_nodeA']}_vs_B({len(match['nodes_B'])}of{MINUTIAE_SUBGRAPH_SIZE})_"
            f"{match['start_nodeB']}.png"
        )
        plot_match_with_context(
            S_A, S_B,                      # macro-subgrafi
            match["subG_A"], match["subG_B"],
            G_A, G_B,
            match["mapping"],
            OUTPUT_FOLDER_SUBGRAPHS,
            f"match_{match['id']}_WITH_CONTEXT.png",
            score=match["score"]
        )


    # --- Stampa Finale dei Grafi Completi con Evidenziazione ---
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

# --- Esecuzione dello script ---
if __name__ == "__main__":
    main()