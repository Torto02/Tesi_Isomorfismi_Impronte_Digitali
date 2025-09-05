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

RADIUS_PERCENTAGE_A            = 0.08
RADIUS_PERCENTAGE_B            = 0.08
MINUTIAE_SUBGRAPH_SIZE         = 6
MIN_MATCH_NODES                = 6
MATCHING_COST_THRESHOLD_REL    = 0.3
MATCHING_MAX_RIDGE_DIFF        = 1
MATCHING_ANGLE_TOLERANCE_DEGREES = 30
MATCHING_MAX_EDGE_LENGTH_RATIO = 2.0

# Nuovi parametri per fattori di ricerca della densità (includili nella cache)
DENSITY_RADIUS_FACTOR         = 0.1  # usato in find_densest_zone_minutia
CANDIDATE_DENSITY_FACTOR      = 0.1   # usato in find_corresponding_minutia_in_B

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

def find_densest_zone_minutia(graph, minutiae_nodes, radius_factor=DENSITY_RADIUS_FACTOR):
    """
    Trova la minuzia nella zona più densa dell'impronta usando densità locale.
    Considera TUTTI i nodi del grafo (incluse le creste) per calcolare la vera densità.
    
    Args:
        graph: Il grafo contenente le posizioni dei nodi
        minutiae_nodes: Lista dei nodi che rappresentano le minuzie
        radius_factor: Fattore del raggio per calcolare densità locale (default: 0.2)
        
    Returns:
        Il nodo della minuzia nella zona più densa
    """
    if not minutiae_nodes:
        return None
    
    if len(minutiae_nodes) < 3:
        # Con poche minuzie, usa quella più centrale
        return find_fallback_central_minutia(graph, minutiae_nodes)
    
    minutiae_positions = [graph.nodes[node]['pos'] for node in minutiae_nodes]
    
    # Calcola dimensione caratteristica dell'impronta basata sulle minuzie
    min_x = min(pos[0] for pos in minutiae_positions)
    max_x = max(pos[0] for pos in minutiae_positions)
    min_y = min(pos[1] for pos in minutiae_positions)
    max_y = max(pos[1] for pos in minutiae_positions)
    
    characteristic_size = math.sqrt((max_x - min_x)**2 + (max_y - min_y)**2)
    
    # Prova raggi multipli per trovare quello che meglio discrimina le zone dense
    test_radii = [0.1, 0.15, 0.2, 0.25, 0.3]
    best_radius = radius_factor * characteristic_size
    
    # Se vogliamo essere conservativi, usa il raggio originale
    search_radius = best_radius
    
    # Ottieni posizioni di TUTTI i nodi del grafo per calcolare la vera densità
    all_positions = [graph.nodes[node]['pos'] for node in graph.nodes()]
    
    # Calcola densità locale per ogni minuzia considerando tutti i nodi del grafo
    density_scores = []
    for i, minutia_node in enumerate(minutiae_nodes):
        minutia_pos = minutiae_positions[i]
        
        # Conta TUTTI i nodi del grafo entro il raggio di ricerca
        neighbors_count = 0
        for other_node in graph.nodes():
            if other_node != minutia_node:  # Escludi la minuzia stessa
                other_pos = graph.nodes[other_node]['pos']
                distance = math.dist(minutia_pos, other_pos)
                if distance <= search_radius:
                    neighbors_count += 1
        
        # Score di densità: numero di nodi vicini diviso per area del cerchio
        area = math.pi * search_radius**2
        density = neighbors_count / area
        
        density_scores.append((minutia_node, density, neighbors_count, minutia_pos))
    
    # Ordina per densità decrescente
    density_scores.sort(key=lambda x: x[1], reverse=True)
    
    # DEBUG: Stampa tutte le densità per analisi
    print(f"\n=== DEBUG: Analisi densità (raggio {search_radius:.2f}) ===")
    print(f"Dimensione caratteristica: {characteristic_size:.2f}")
    print(f"Fattore raggio: {radius_factor}")
    print(f"Nodi totali nel grafo: {graph.number_of_nodes()}")
    print(f"Minuzie totali: {len(minutiae_nodes)}")
    print("\nDensità per ogni minuzia (ordinate per densità):")
    for idx, (node, density, neighbors, pos) in enumerate(density_scores[:10]):  # Top 10
        print(f"  {idx+1}. Nodo {node:>4} pos({pos[0]:>6.1f},{pos[1]:>6.1f}) → {neighbors:>4} nodi, densità {density:.8f}")
    
    # Prendi la minuzia con la densità più alta
    selected_node, density, neighbors, pos = density_scores[0]
    
    print(f"\nZona più densa selezionata:")
    print(f"  - Minuzia: nodo {selected_node}")
    print(f"  - Posizione: ({pos[0]:.2f}, {pos[1]:.2f})")
    print(f"  - Densità: {density:.8f} nodi/area")
    print(f"  - Nodi entro raggio: {neighbors}/{graph.number_of_nodes()}")
    
    return selected_node

def find_corresponding_minutia_in_B(graph_A, graph_B, minutiae_A, minutiae_B, selected_A, M3_A, M3_B):
    """
    Trova la minuzia in B che meglio corrisponde alla minuzia selezionata in A,
    basandosi sulla posizione relativa e densità locale simile.
    
    Args:
        graph_A, graph_B: I grafi delle due impronte
        minutiae_A, minutiae_B: Liste delle minuzie per entrambe le impronte  
        selected_A: Nodo della minuzia selezionata in A
        M3_A, M3_B: Matrici di distanza per entrambe le impronte
        
    Returns:
        Il nodo della minuzia corrispondente in B
    """
    if not minutiae_B:
        return None
    
    # Ottieni posizione e proprietà della minuzia selezionata in A
    pos_A = graph_A.nodes[selected_A]['pos']
    positions_A = [graph_A.nodes[node]['pos'] for node in minutiae_A]
    positions_B = [graph_B.nodes[node]['pos'] for node in minutiae_B]
    
    # Calcola posizione relativa di selected_A rispetto al centroide di A
    centroid_A = (
        sum(pos[0] for pos in positions_A) / len(positions_A),
        sum(pos[1] for pos in positions_A) / len(positions_A)
    )
    
    centroid_B = (
        sum(pos[0] for pos in positions_B) / len(positions_B),
        sum(pos[1] for pos in positions_B) / len(positions_B)
    )
    
    # Vettore relativo da centroide A alla minuzia selezionata
    relative_vector = (pos_A[0] - centroid_A[0], pos_A[1] - centroid_A[1])
    
    # Calcola scala relativa tra le due impronte
    size_A = max(math.dist(pos, centroid_A) for pos in positions_A)
    size_B = max(math.dist(pos, centroid_B) for pos in positions_B)
    scale_factor = size_B / size_A if size_A > 0 else 1.0
    
    # Posizione target in B (scalata)
    target_pos_B = (
        centroid_B[0] + relative_vector[0] * scale_factor,
        centroid_B[1] + relative_vector[1] * scale_factor
    )
    
    # Trova candidati in B vicini alla posizione target
    candidates = []
    for node_B in minutiae_B:
        pos_B = graph_B.nodes[node_B]['pos']
        distance_to_target = math.dist(pos_B, target_pos_B)
        
        # Calcola densità locale in B per questo nodo (usa costante invece di 0.15)
        search_radius = CANDIDATE_DENSITY_FACTOR * size_B
        neighbors_count = sum(
            1 for other_node in minutiae_B
            if other_node != node_B and 
               math.dist(pos_B, graph_B.nodes[other_node]['pos']) <= search_radius
        )
        density_B = neighbors_count / (math.pi * search_radius**2) if search_radius > 0 else 0
        
        candidates.append((node_B, distance_to_target, density_B, pos_B))
    
    # Calcola densità di riferimento della minuzia selezionata in A
    search_radius_A = CANDIDATE_DENSITY_FACTOR * size_A
    neighbors_A = sum(
        1 for other_node in minutiae_A
        if other_node != selected_A and 
           math.dist(pos_A, graph_A.nodes[other_node]['pos']) <= search_radius_A
    )
    density_A = neighbors_A / (math.pi * search_radius_A**2) if search_radius_A > 0 else 0
    
    # Score combinato: distanza dalla posizione target + differenza di densità
    def combined_score(candidate):
        node_B, dist, density_B, pos_B = candidate
        distance_score = dist / size_B  # Normalizzato
        density_diff = abs(density_A - density_B)
        return distance_score + 0.5 * density_diff  # Peso 50% per densità
    
    # Seleziona il migliore candidato
    best_candidate = min(candidates, key=combined_score)
    selected_B, best_distance, best_density, best_pos = best_candidate
    
    print(f"Minuzia corrispondente trovata in B:")
    print(f"  - Minuzia A selezionata: nodo {selected_A} a ({pos_A[0]:.2f}, {pos_A[1]:.2f})")
    print(f"  - Minuzia B corrispondente: nodo {selected_B} a ({best_pos[0]:.2f}, {best_pos[1]:.2f})")
    print(f"  - Distanza da posizione target: {best_distance:.2f}")
    print(f"  - Densità A: {density_A:.6f}, Densità B: {best_density:.6f}")
    print(f"  - Fattore di scala A->B: {scale_factor:.3f}")
    
    return selected_B

def find_intermediate_zone_minutia(graph, minutiae_nodes, angle_start=0, angle_end=45, max_ridges=5):
    """
    Trova minuzie in una zona intermedia tra centro e bordo con criteri specifici:
    - Posizionate a metà distanza tra centro e bordo
    - All'interno di un settore angolare specificato (es. 0-45 gradi)
    - Limitate a un massimo di ridge paralleli
    
    Args:
        graph: Il grafo contenente le posizioni dei nodi
        minutiae_nodes: Lista dei nodi che rappresentano le minuzie
        angle_start: Angolo iniziale del settore in gradi (default: 0)
        angle_end: Angolo finale del settore in gradi (default: 45)
        max_ridges: Massimo numero di ridge paralleli da considerare (default: 5)
        
    Returns:
        Il nodo della minuzia selezionata nella zona intermedia
    """
    if not minutiae_nodes:
        return None
    
    # Calcola il centroide e i bounds delle minuzie
    positions = [graph.nodes[node]['pos'] for node in minutiae_nodes]
    centroid_x = sum(pos[0] for pos in positions) / len(positions)
    centroid_y = sum(pos[1] for pos in positions) / len(positions)
    centroid = (centroid_x, centroid_y)
    
    # Calcola raggio massimo (distanza dal centro al punto più lontano)
    max_radius = max(math.dist(pos, centroid) for pos in positions)
    
    # Definisci la zona intermedia (tra 40% e 70% del raggio massimo)
    inner_radius = 0.4 * max_radius
    outer_radius = 0.7 * max_radius
    
    # Filtra minuzie nella zona intermedia
    intermediate_candidates = []
    for node in minutiae_nodes:
        node_pos = graph.nodes[node]['pos']
        distance = math.dist(node_pos, centroid)
        
        if inner_radius <= distance <= outer_radius:
            # Calcola angolo rispetto al centroide (in gradi, 0-360)
            angle = math.degrees(math.atan2(node_pos[1] - centroid_y, node_pos[0] - centroid_x))
            if angle < 0:
                angle += 360
            
            # Verifica se è nel settore angolare specificato
            if angle_start <= angle <= angle_end:
                intermediate_candidates.append((node, distance, angle))
    
    if not intermediate_candidates:
        print(f"Nessuna minuzia trovata nella zona intermedia (settore {angle_start}-{angle_end}°)")
        # Fallback: usa la minuzia più centrale tradizionale
        return find_fallback_central_minutia(graph, minutiae_nodes)
    
    # Ordina per distanza dalla zona centrale della fascia intermedia
    target_radius = (inner_radius + outer_radius) / 2
    intermediate_candidates.sort(key=lambda x: abs(x[1] - target_radius))
    
    # Limita a max_ridges candidati
    selected_candidates = intermediate_candidates[:max_ridges]
    
    # Seleziona il primo candidato (più vicino alla zona target)
    selected_node, selected_distance, selected_angle = selected_candidates[0]
    
    print(f"Centroide calcolato: ({centroid_x:.2f}, {centroid_y:.2f})")
    print(f"Zona intermedia: raggio {inner_radius:.2f} - {outer_radius:.2f}")
    print(f"Settore angolare: {angle_start}° - {angle_end}°")
    print(f"Minuzia selezionata: nodo {selected_node}")
    print(f"  - Distanza dal centro: {selected_distance:.2f}")
    print(f"  - Angolo: {selected_angle:.1f}°")
    print(f"  - Candidati nella zona: {len(intermediate_candidates)}")
    print(f"  - Candidati considerati: {len(selected_candidates)}")
    
    return selected_node

def find_fallback_central_minutia(graph, minutiae_nodes):
    """
    Fallback: trova la minuzia più centrale (logica originale)
    """
    positions = [graph.nodes[node]['pos'] for node in minutiae_nodes]
    centroid_x = sum(pos[0] for pos in positions) / len(positions)
    centroid_y = sum(pos[1] for pos in positions) / len(positions)
    centroid = (centroid_x, centroid_y)
    
    min_distance = float('inf')
    most_central_node = None
    
    for node in minutiae_nodes:
        node_pos = graph.nodes[node]['pos']
        distance = math.dist(node_pos, centroid)
        
        if distance < min_distance:
            min_distance = distance
            most_central_node = node
    
    print(f"Fallback: minuzia centrale nodo {most_central_node} a distanza {min_distance:.2f}")
    return most_central_node

def generate_cache_key(fingerprint_name, central_node, radius_percentage, subgraph_size, matching_params=None):
    """
    Genera una chiave univoca per la cache basata sui parametri dell'elaborazione.
    Include tutti i criteri di matching per garantire l'invalidazione della cache
    quando qualsiasi parametro viene modificato.
    
    Args:
        fingerprint_name: Nome dell'impronta
        central_node: Nodo centrale selezionato
        radius_percentage: Percentuale del raggio usata
        subgraph_size: Dimensione dei sottografi
        matching_params: Dizionario con i parametri di matching aggiuntivi
        
    Returns:
        Chiave MD5 hash basata su tutti i parametri
    """
    # Parametri base
    key_parts = [
        f"name={fingerprint_name}",
        f"node={central_node}",
        f"radius={radius_percentage}",
        f"size={subgraph_size}"
    ]
    
    # Aggiungi parametri di matching se forniti
    if matching_params:
        for key, value in sorted(matching_params.items()):
            key_parts.append(f"{key}={value}")
    
    key_string = "_".join(key_parts)
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
    
    # Selezione automatica della minuzia nella zona più densa
    start_nodeA = find_densest_zone_minutia(G_A, minutiaeA)
    print(f"Minuzia A selezionata nella zona più densa: nodo {start_nodeA}")
    
    # --- Verifica cache per impronta A ---
    # Crea un dizionario con tutti i parametri di matching per la chiave della cache
    matching_params = {
        'cost_threshold': MATCHING_COST_THRESHOLD_REL,
        'max_ridge_diff': MATCHING_MAX_RIDGE_DIFF,
        'angle_tolerance': MATCHING_ANGLE_TOLERANCE_DEGREES,
        'edge_length_ratio': MATCHING_MAX_EDGE_LENGTH_RATIO,
        # aggiunti i fattori di densità e qualsiasi parametro rilevante per l'estrazione
        'density_radius_factor': DENSITY_RADIUS_FACTOR,
        'candidate_density_factor': CANDIDATE_DENSITY_FACTOR
    }
    
    cache_key = generate_cache_key(
        impronte[idxA], 
        start_nodeA, 
        RADIUS_PERCENTAGE_A, 
        MINUTIAE_SUBGRAPH_SIZE,
        matching_params
    )
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
            'matching_params': matching_params,
            'timestamp': datetime.datetime.now().isoformat()
        }
        save_to_cache(cache_key, cache_data, CACHE_FOLDER)
    
    # Plot sottografo A (sempre necessario per questa esecuzione)
    # plot_and_save_subgraph(
    #     S_A, G_A, start_nodeA,
    #     OUTPUT_FOLDER_GRAPHS,
    #     f"macro_subgraph_A_{impronte[idxA]}_nodo{start_nodeA}.png"
    # )

    # --- Estrazione sottografo locale B (selezione intelligente) ---
    minutiaeB = sorted(n for n,d in G_B.nodes(data=True) if d.get('type') in ('ending','bifurcation'))
    print(f"Trovate {len(minutiaeB)} minuzie nell'impronta B")
    
    # Trova la minuzia corrispondente in B basata su posizione relativa e densità
    closestB = find_corresponding_minutia_in_B(G_A, G_B, minutiaeA, minutiaeB, start_nodeA, M3_A, M3_B)
    print(f"Minuzia B corrispondente selezionata: nodo {closestB}")
    
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
        # plot_final_graphs(
        # G_A, G_B,
        # set(), set(),
        # centerA_coords=G_A.nodes[start_nodeA]['pos'],
        # radiusA=radiusA,
        # centerB_coords=G_B.nodes[closestB]['pos'],
        # radiusB=radiusB,
        # output_folder=OUTPUT_FOLDER_FINAL_GRAPHS,
        # filename=f"final_matches_{impronte[idxA]}_vs_{impronte[idxB]}.png",
        # all_matches=[]
        # )   

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

    # The cache contains:
    # - S_A: The local subgraph extracted around the central minutia within radiusA
    # - sub_subgraphs_A: All connected subgraphs of minutiae of specified size from S_A
    # - radiusA: The radius used for subgraph extraction (calculated from RADIUS_PERCENTAGE_A)
    # - fingerprint_name: The name of the processed fingerprint
    # - central_node: The node ID of the central minutia used as starting point
    # - radius_percentage: The percentage used to calculate the radius
    # - subgraph_size: The size of minutiae subgraphs that were extracted
    # - timestamp: When the cache was created

    # This caching mechanism saves significant computation time for frequently 
    # processed fingerprints by storing the expensive subgraph extraction results.
    # The key is based on fingerprint name, central node, radius percentage, and subgraph size.

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

    for rank, (i, j, mapping, score) in enumerate(valid, start=1):
        print(f"{rank}. A#{i} vs B#{j} → score {score:.4f}")

    # --- Plot dei match --- 
    for rank, (i, j, mapping, score) in enumerate(valid, start=1):
        subG_A = sub_subgraphs_A[i][1]
        subG_B = sub_subgraphs_B[j][1]

        logger.log(
            idA=impronte[idxA],
            idB=impronte[idxB],
            relation="unknown",  # oppure da un dizionario, se hai pairs_metadata
            subgraph_id=f"A{i}_B{j}_rank{rank}",
            nodes_mapped=len(mapping),
            score=score,
            pair_details={
                "mapping": mapping,
                "subgraphA_nodes": list(subG_A.nodes),
                "subgraphB_nodes": list(subG_B.nodes)
            }
        )


        plot_mapping(
            subG_A, subG_B,
            G_A, G_B,
            mapping,
            OUTPUT_FOLDER_SUBGRAPHS,
            f"match_{rank}_score_{score:.4f}_A({len(mapping)})_"
            f"{sub_subgraphs_A[i][0]}_vs_B({len(mapping)})_{sub_subgraphs_B[j][0]}.png"
        )

        plot_match_with_context(
            S_A, S_B,
            subG_A, subG_B,
            G_A, G_B,
            mapping,
            OUTPUT_FOLDER_SUBGRAPHS,
            f"match_{rank}_WITH_CONTEXT.png",
            score=score
        )

    #     # plot_chirality_check(
    #     #     subG_A, subG_B,
    #     #     mapping,
    #     #     OUTPUT_FOLDER_SUBGRAPHS,
    #     #     f"match_{rank}_CHIRALITY_CHECK.png",
    #     #     score=score
    #     # )

    # --- Plot finale dei grafi completi con evidenziazione ---
    all_nodes_A = set().union(*(m[2].keys() for m in valid))
    all_nodes_B = set().union(*(m[2].values() for m in valid))
    plot_final_graphs(
        G_A, G_B,
        all_nodes_A, all_nodes_B,
        centerA_coords=G_A.nodes[start_nodeA]['pos'],
        radiusA=radiusA,
        centerB_coords=G_B.nodes[closestB]['pos'],
        radiusB=radiusB,
        output_folder=OUTPUT_FOLDER_FINAL_GRAPHS,
        filename=f"final_matches_{impronte[idxA]}_vs_{impronte[idxB]}.png",
        all_matches=[{'mapping':m[2], 'score':m[3]} for m in valid]
    )

    print("\nElaborazione completata.")
    if cached_data is None:
        print(f"I dati per l'impronta A sono stati salvati nella cache con chiave: {cache_key}")

if __name__ == '__main__':
    main()