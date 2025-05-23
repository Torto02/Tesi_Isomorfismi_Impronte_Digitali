import os
import math
import networkx as nx
import datetime

# Importa funzioni dai moduli creati
from graph_processing import load_fingerprint_and_compute
from subgraph_operations import get_subgraph_within_radius, get_connected_subgraphs_of_minutiae, get_connected_subgraphs_of_minutiae_parallel, get_random_minutiae_subgraph_in_radius
from matching import match_subgraph
from plotting import plot_and_save_subgraph, plot_mapping, plot_final_graphs,plot_match_with_context

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
# MINUTIAE_SUBGRAPH_SIZE = 6 # Dimensione dei sotto-sottografi di minuzie da cercare (SOSTITUITO)
NUM_MINUTIAE_TO_SELECT = 5 # Numero di minuzie reali da selezionare per i nuovi sottografi
RADIUS_PIXELS = 4         # Raggio fisso in pixel per la selezione delle minuzie vicine (ESEMPIO, da calibrare)
MIN_MATCH_NODES = 4        # Numero minimo di nodi matchati per considerare un match valido (>=NUM_MINUTIAE_TO_SELECT se si vuole identità)
MATCHING_COST_THRESHOLD_REL = 0.7 # Soglia differenza relativa per M1 cost (0.6 = 60% di tolleranza)
MATCHING_MAX_RIDGE_DIFF = 2     # Soglia differenza assoluta per M_scavalcamenti
MATCHING_ANGLE_TOLERANCE_DEGREES = 35 # Soglia tolleranza angolare in gradi (es. +/- 35 gradi)

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

# Puoi aggiungere questa funzione in main_script.py o creare un nuovo script

def analyze_pair_details(all_matches, match_id, pair):
    """
    Analizza e visualizza i dettagli di una specifica coppia di nodi in un match.
    
    Args:
        all_matches: lista di tutti i match
        match_id: ID del match da analizzare
        pair: tupla (nodeA1, nodeA2) che identifica la coppia
    """
    # Trova il match specifico
    match = next((m for m in all_matches if m['id'] == match_id), None)
    if not match:
        print(f"Match #{match_id} non trovato.")
        return
    
    # Trova i dettagli della coppia
    if pair not in match['pair_details']:
        print(f"Coppia {pair} non trovata nel match #{match_id}.")
        return
    
    details = match['pair_details'][pair]
    mapping = match['mapping']
    nodeA1, nodeA2 = pair
    nodeB1, nodeB2 = mapping[nodeA1], mapping[nodeA2]
    
    print(f"\n--- Analisi Dettagliata Coppia ({nodeA1}, {nodeA2}) → ({nodeB1}, {nodeB2}) ---")
    print(f"Score totale coppia: {details['total_score']:.4f}")
    
    # Dettagli scavalcamenti
    print("\nScavalcamenti:")
    print(f"  Grafo A: {details.get('ridge_A', 'N/A')}")
    print(f"  Grafo B: {details.get('ridge_B', 'N/A')}")
    print(f"  Score: {details.get('ridge_score', 'N/A'):.4f}")
    
    # Dettagli costi
    print("\nCosti percorso:")
    print(f"  Grafo A: {details.get('cost_A', 'N/A')}")
    print(f"  Grafo B: {details.get('cost_B', 'N/A')}")
    print(f"  Score: {details.get('cost_score', 'N/A'):.4f}")
    
    # Dettagli angoli
    print("\nAngoli:")
    print(f"  Grafo A: {details.get('angle_A', 'N/A'):.2f}°")
    print(f"  Grafo B: {details.get('angle_B', 'N/A'):.2f}°")
    print(f"  Differenza: {details.get('angle_diff', 'N/A'):.2f}°")
    print(f"  Score: {details.get('angle_score', 'N/A'):.4f}")
    
    # Eventuali errori
    if 'error' in details:
        print(f"\nErrori: {details['error']}")

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
    print("\\n--- Caricamento/Calcolo Dati Impronta A ---")
    # La funzione ora ritorna G, M1, M_scavalcamenti, M3, node_list_for_matrix
    G_A, M1_A, M_scavalcamenti_A, M3_A, node_list_A = load_fingerprint_and_compute(folder_A, OUTPUT_FOLDER_MATRICES)
    if G_A is None or M1_A is None or M_scavalcamenti_A is None or M3_A is None or node_list_A is None:
        print(f"Errore critico nel caricamento/calcolo per l'impronta A: {improntaA_nome}. Interruzione.")
        return
    print(f"Caricata Impronta A: {improntaA_nome}, Nodi={G_A.number_of_nodes()}, Archi={G_A.number_of_edges()}")


    print("\\n--- Caricamento/Calcolo Dati Impronta B ---")
    G_B, M1_B, M_scavalcamenti_B, M3_B, node_list_B = load_fingerprint_and_compute(folder_B, OUTPUT_FOLDER_MATRICES)
    if G_B is None or M1_B is None or M_scavalcamenti_B is None or M3_B is None or node_list_B is None:
        print(f"Errore critico nel caricamento/calcolo per l'impronta B: {improntaB_nome}. Interruzione.")
        return
    print(f"Caricata Impronta B: {improntaB_nome}, Nodi={G_B.number_of_nodes()}, Archi={G_B.number_of_edges()}")


    # --- Selezione Minuzia di Partenza in A (non più necessaria per il nuovo metodo) ---
    # La logica di selezione della minuzia di partenza e l'estrazione di S_A e S_B basata su RADIUS_PERCENTAGE
    # viene sostituita dalla nuova logica di iterazione e get_random_minutiae_subgraph_in_radius.
    # Manteniamo per ora la selezione di una minuziaA_id e minuziaB_id per il plot finale,
    # ma non guideranno più l'estrazione dei sottografi per il matching.

    # --- Selezione Minuzia di Riferimento in A (per plot finale) ---
    print("\\n--- Selezione Minuzia di Riferimento (per plot finale) ---")
    minutia_nodesA_all = sorted([n for n, data in G_A.nodes(data=True) if data.get('type') in ('ending','bifurcation')])
    if not minutia_nodesA_all:
        print(f"Errore: Nessuna minuzia ('ending' o 'bifurcation') trovata in {improntaA_nome}.")
        return

    # Scegliamo una minuzia di riferimento in A (es. la prima) per il plot finale.
    # Questo non influenzerà il matching che itera su tutte le minuzie.
    minuziaA_ref_id = minutia_nodesA_all[0]
    print(f"Minuzia di riferimento in A (per plot): {minuziaA_ref_id}")
    
    # Trova la più vicina in B per il plot finale
    minutia_nodesB_all = sorted([n for n, data in G_B.nodes(data=True) if data.get('type') in ('ending','bifurcation')])
    if not minutia_nodesB_all:
        print(f"Errore: Nessuna minuzia trovata in {improntaB_nome}.")
        return

    pos_minuziaA_ref = G_A.nodes[minuziaA_ref_id]['pos']
    closest_minutiaB_ref_id = None
    min_euclidean_dist_ref = float('inf')
    for nodeB_id_ref in minutia_nodesB_all:
        try:
            if nodeB_id_ref not in G_B: continue
            pos_nodeB_ref = G_B.nodes[nodeB_id_ref]['pos']
            distance = math.dist(pos_minuziaA_ref, pos_nodeB_ref)
            if distance < min_euclidean_dist_ref:
                min_euclidean_dist_ref = distance
                closest_minutiaB_ref_id = nodeB_id_ref
        except KeyError:
            continue 
    minuziaB_ref_id = closest_minutiaB_ref_id if closest_minutiaB_ref_id else minutia_nodesB_all[0]
    print(f"Minuzia di riferimento in B (per plot): {minuziaB_ref_id}")


    #! --- NUOVA LOGICA: Ricerca e Matching dei Sottografi Casuali Basati su Raggio ---
    print(f"\\n--- Ricerca Sottografi Casuali di {NUM_MINUTIAE_TO_SELECT} Minuzie (Raggio {RADIUS_PIXELS}px) ---")

    all_matches = []
    match_counter = 0
    processed_central_nodes_A = 0

    # Itera su tutte le minuzie reali in A come possibili nodi centrali
    real_minutiae_A = [n for n, data in G_A.nodes(data=True) if data.get('type') != 'added']
    real_minutiae_B = [n for n, data in G_B.nodes(data=True) if data.get('type') != 'added']

    print(f"Inizio generazione e matching sottografi...")
    print(f"Minuzie reali in A: {len(real_minutiae_A)}, Minuzie reali in B: {len(real_minutiae_B)}")

    # Per evitare di riprocessare coppie di sottografi identiche se la selezione casuale produce gli stessi nodi
    # (anche se con la componente casuale e i percorsi minimi è meno probabile avere duplicati esatti di S_A/S_B)
    # Una strategia più robusta contro i duplicati di *match* è controllare il mapping, come già fatto dopo.
    
    # Definisci la funzione peso per i cammini minimi (se vuoi usare i costi degli archi)
    # Ad esempio, se gli archi hanno un attributo 'cost':
    # shortest_path_weight_func = lambda u, v, d: d.get('cost', 1.0)
    # Se vuoi cammini minimi basati sul numero di archi (non pesati):
    shortest_path_weight_func = None


    for central_node_A in real_minutiae_A:
        processed_central_nodes_A += 1
        if processed_central_nodes_A % 10 == 0: # Log ogni 10 nodi centrali di A
            print(f"  Processando nodo centrale A #{processed_central_nodes_A}/{len(real_minutiae_A)}: {central_node_A}")

        S_A = get_random_minutiae_subgraph_in_radius(
            G_A, M3_A, node_list_A, central_node_A, 
            RADIUS_PIXELS, NUM_MINUTIAE_TO_SELECT,
            shortest_path_weight_func=shortest_path_weight_func
        )
        if S_A is None or len([n for n in S_A.nodes if S_A.nodes[n].get('type') != 'added']) < NUM_MINUTIAE_TO_SELECT:
            continue # Sottografo non valido o troppo piccolo

        # Plot del sottografo S_A generato (opzionale, può generare molti file)
        # plot_and_save_subgraph(
        #     S_A, G_A, central_node_A, OUTPUT_FOLDER_SUBGRAPHS, # Usa OUTPUT_FOLDER_SUBGRAPHS
        #     f"S_A_cen{central_node_A}_r{RADIUS_PIXELS}_n{NUM_MINUTIAE_TO_SELECT}.png"
        # )

        for central_node_B in real_minutiae_B:
            S_B = get_random_minutiae_subgraph_in_radius(
                G_B, M3_B, node_list_B, central_node_B,
                RADIUS_PIXELS, NUM_MINUTIAE_TO_SELECT, # Usa lo stesso raggio per B, o definisci RADIUS_PIXELS_B
                shortest_path_weight_func=shortest_path_weight_func
            )
            if S_B is None or len([n for n in S_B.nodes if S_B.nodes[n].get('type') != 'added']) < NUM_MINUTIAE_TO_SELECT:
                continue
            
            # Plot del sottografo S_B generato (opzionale)
            # plot_and_save_subgraph(
            #     S_B, G_B, central_node_B, OUTPUT_FOLDER_SUBGRAPHS,
            #     f"S_B_cen{central_node_B}_r{RADIUS_PIXELS}_n{NUM_MINUTIAE_TO_SELECT}.png"
            # )

            # Esegui il matching tra S_A e S_B
            # La funzione match_subgraph si aspetta che i nodi reali siano identificabili
            # e che le matrici M1 e M_scavalcamenti siano relative ai grafi originali G_A, G_B.
            success, mapping, score, pair_details = match_subgraph(
                S_A, S_B, # I sottografi S_A e S_B contengono nodi da G_A e G_B
                M1_A, M1_B, # Matrici globali
                M_scavalcamenti_A, M_scavalcamenti_B, # Matrici globali
                cost_threshold_rel=MATCHING_COST_THRESHOLD_REL,
                max_ridge_diff=MATCHING_MAX_RIDGE_DIFF,
                angle_tolerance_degrees=MATCHING_ANGLE_TOLERANCE_DEGREES
            )
            
            if success and len(mapping) >= MIN_MATCH_NODES:
                # Converti il mapping in una rappresentazione immutabile per il controllo dei duplicati
                # Questo controllo sui mapping duplicati è importante
                # mapping_tuple = tuple(sorted((a, b) for a, b in mapping.items()))
                # if mapping_tuple in found_mappings: # found_mappings deve essere definito prima del loop
                #     continue
                # found_mappings.add(mapping_tuple) # Aggiungi se non è un duplicato

                match_counter += 1
                matched_nodesA_map = list(mapping.keys())
                matched_nodesB_map = [mapping[n] for n in matched_nodesA_map]
                
                current_match_result = {
                    'id': match_counter,
                    'mapping': mapping,
                    'nodes_A': matched_nodesA_map,
                    'nodes_B': matched_nodesB_map,
                    'score': score,
                    'pair_details': pair_details,
                    'subG_A': S_A.copy(), # Salva una copia per evitare modifiche impreviste
                    'subG_B': S_B.copy(),
                    'central_node_A': central_node_A, # Nodo usato per generare S_A
                    'central_node_B': central_node_B  # Nodo usato per generare S_B
                }
                all_matches.append(current_match_result)

                # Stampa informazioni sul match (meno verboso durante il ciclo)
                if match_counter % 20 == 0: # Log ogni 20 match trovati
                     print(f"    Trovato Match #{match_counter}! Score: {score:.4f}. Centrali A:{central_node_A}, B:{central_node_B}")


    # Ordina i match per score (dal migliore al peggiore)
    all_matches.sort(key=lambda x: x['score'], reverse=True)
    
    # Filtra ulteriormente i duplicati basati sul mapping esatto, mantenendo quello con score più alto
    # Questo è utile se la logica precedente non ha catturato tutti i duplicati o se si preferisce
    # un approccio post-processato.
    unique_matches_by_mapping = {}
    for m in all_matches:
        mapping_tuple = tuple(sorted(m['mapping'].items()))
        if mapping_tuple not in unique_matches_by_mapping or m['score'] > unique_matches_by_mapping[mapping_tuple]['score']:
            unique_matches_by_mapping[mapping_tuple] = m
    
    all_matches = list(unique_matches_by_mapping.values())
    all_matches.sort(key=lambda x: x['score'], reverse=True) # Riordina dopo la deduplicazione

    # Aggiorna gli ID dei match dopo la deduplicazione
    for i, match_item in enumerate(all_matches):
        match_item['id'] = i + 1


    print(f"\\n--- Risultato Matching (Nuova Metodologia) ---")
    print(f"Totale nodi centrali A processati: {processed_central_nodes_A}")
    print(f"Numero di match unici trovati (>= {MIN_MATCH_NODES} nodi): {len(all_matches)}")

    # Aggiorna i set globali di nodi matchati dai match filtrati e ordinati
    matched_nodes_A_global = set()
    matched_nodes_B_global = set()
    for match in all_matches:
        matched_nodes_A_global.update(match['nodes_A'])
        matched_nodes_B_global.update(match['nodes_B'])

    print(f"Nodi totali coinvolti in match validi in A: {len(matched_nodes_A_global)}")
    print(f"Nodi totali coinvolti in match validi in B: {len(matched_nodes_B_global)}")


    # Stampare i risultati ordinati
    print(f"\\n--- Graduatoria dei {len(all_matches)} Match Trovati (Nuova Metodologia) ---")
    for i, match in enumerate(all_matches):
        print(f"{i+1}. Match #{match['id']} - Score: {match['score']:.4f} - Centrali A:{match['central_node_A']}, B:{match['central_node_B']}")
        # print(f"   Nodi A: {match['nodes_A']}, Nodi B: {match['nodes_B']}")


    # Plotting dei migliori match
    # Potresti voler plottare solo i top N match per evitare troppi file
    num_matches_to_plot = min(len(all_matches), 10) # Esempio: plotta i top 10
    print(f"\\n--- Plotting dei migliori {num_matches_to_plot} match ---")

    for i, match in enumerate(all_matches[:num_matches_to_plot]):
        plot_filename_base = (
            f"match_{match['id']:03d}_score_{match['score']:.4f}_"
            f"A_cen{match['central_node_A']}_B_cen{match['central_node_B']}"
        )
        
        # Plot dei due sottografi S_A e S_B con il mapping
        plot_mapping(
            match['subG_A'], match['subG_B'],
            G_A, G_B, # Grafi originali per contesto posizioni
            match['mapping'],
            OUTPUT_FOLDER_SUBGRAPHS,
            f"{plot_filename_base}.png",
            score=match['score']
        )
        
        # Plot con contesto (se la funzione è ancora rilevante e funzionante con S_A, S_B)
        # La funzione plot_match_with_context potrebbe aver bisogno di aggiustamenti
        # se S_A e S_B ora sono generati diversamente (non sono più "macro" subgrafi).
        # Per ora, la commentiamo se non siamo sicuri della sua compatibilità diretta.
        # plot_match_with_context(
        #     G_A, G_B, # Passiamo i grafi completi come "macro"
        #     match["subG_A"], match["subG_B"], # E i sottografi specifici del match
        #     G_A, G_B, # Di nuovo G_A, G_B per il contesto interno alla funzione
        #     match["mapping"],
        #     OUTPUT_FOLDER_SUBGRAPHS,
        #     f"{plot_filename_base}_WITH_CONTEXT.png",
        #     score=match["score"]
        # )
        print(f"  Plot salvato per Match #{match['id']}: {plot_filename_base}.png")


    # --- Stampa Finale dei Grafi Completi con Evidenziazione ---
    print("\\n--- Generazione Plot Finale (Nuova Metodologia) ---")
    # Usa le minuzie di riferimento per centrare il plot finale, se disponibili
    centerA_coords_plot = G_A.nodes[minuziaA_ref_id].get('pos') if minuziaA_ref_id in G_A else None
    centerB_coords_plot = G_B.nodes[minuziaB_ref_id].get('pos') if minuziaB_ref_id in G_B else None
    
    # Per i raggi del plot finale, potremmo usare un valore fisso o calcolarlo
    # Se RADIUS_PERCENTAGE_A/B non sono più usati per l'estrazione, potremmo ricalcolarli qui
    # o usare un valore indicativo. Per ora, usiamo i valori originali se disponibili.
    final_plot_radiusA = RADIUS_PERCENTAGE_A * find_max_finite_distance(M3_A) if M3_A else 100
    final_plot_radiusB = RADIUS_PERCENTAGE_B * find_max_finite_distance(M3_B) if M3_B else 100


    plot_final_graphs(
        G_A, G_B,
        matched_nodes_A_global, # Nodi globalmente matchati
        matched_nodes_B_global,
        centerA_coords=centerA_coords_plot,
        radiusA=final_plot_radiusA, # Raggio per il cerchio di visualizzazione
        centerB_coords=centerB_coords_plot,
        radiusB=final_plot_radiusB, # Raggio per il cerchio di visualizzazione
        output_folder=OUTPUT_FOLDER_FINAL_GRAPHS,
        filename=f"final_matches_NEW_{improntaA_nome}_vs_{improntaB_nome}.png",
        all_matches=all_matches # Passa tutti i match per eventuale visualizzazione dettagliata nel plot
    )

    print("\\n--- Elaborazione Completata (Nuova Metodologia) ---")

# --- Esecuzione dello script ---
if __name__ == "__main__":
    main()