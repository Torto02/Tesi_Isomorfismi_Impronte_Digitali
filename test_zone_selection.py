#!/usr/bin/env python3
"""
Script di test per verificare la nuova logica di selezione zona intermedia
"""

import sys
sys.path.append('.')

from main_script import find_intermediate_zone_minutia, find_fallback_central_minutia
from graph_processing import load_fingerprint_and_compute
import math

# Test con una impronta specifica
BASE_FOLDER_IMPRONTE = "/Users/riccardotortorelli/Desktop/Tesi/Archivio/"
OUTPUT_FOLDER_MATRICES = "/Users/riccardotortorelli/Desktop/Tesi/OutputMatrices"

def test_zone_selection():
    """Test della nuova logica di selezione zona intermedia"""
    
    # Carica una impronta di test
    test_folder = BASE_FOLDER_IMPRONTE + "01_Ay_03_01"
    print(f"Testing zone selection with: {test_folder}")
    
    try:
        G, _, M_scav, M3 = load_fingerprint_and_compute(test_folder, OUTPUT_FOLDER_MATRICES)
        print(f"Loaded fingerprint: nodes={G.number_of_nodes()}, edges={G.number_of_edges()}")
        
        # Trova le minuzie
        minutiae = sorted(n for n, d in G.nodes(data=True) if d.get('type') in ('ending', 'bifurcation'))
        print(f"Found {len(minutiae)} minutiae")
        
        if len(minutiae) < 10:
            print("Not enough minutiae for meaningful test")
            return
        
        print("\n=== TEST 1: Zona intermedia settore 0-45° ===")
        selected_node_1 = find_intermediate_zone_minutia(G, minutiae, angle_start=0, angle_end=45, max_ridges=5)
        
        print("\n=== TEST 2: Zona intermedia settore 90-135° ===")
        selected_node_2 = find_intermediate_zone_minutia(G, minutiae, angle_start=90, angle_end=135, max_ridges=5)
        
        print("\n=== TEST 3: Zona intermedia settore 180-225° ===")  
        selected_node_3 = find_intermediate_zone_minutia(G, minutiae, angle_start=180, angle_end=225, max_ridges=5)
        
        print("\n=== TEST 4: Confronto con metodo originale ===")
        original_node = find_fallback_central_minutia(G, minutiae)
        
        # Calcola statistiche
        positions = [G.nodes[node]['pos'] for node in minutiae]
        centroid_x = sum(pos[0] for pos in positions) / len(positions)
        centroid_y = sum(pos[1] for pos in positions) / len(positions)
        centroid = (centroid_x, centroid_y)
        
        print(f"\nComparison of selected nodes:")
        for label, node in [("Settore 0-45°", selected_node_1), 
                           ("Settore 90-135°", selected_node_2),
                           ("Settore 180-225°", selected_node_3),
                           ("Metodo originale", original_node)]:
            if node:
                pos = G.nodes[node]['pos']
                dist_from_center = math.dist(pos, centroid)
                angle = math.degrees(math.atan2(pos[1] - centroid_y, pos[0] - centroid_x))
                if angle < 0:
                    angle += 360
                print(f"  {label}: nodo {node}, distanza {dist_from_center:.2f}, angolo {angle:.1f}°")
            else:
                print(f"  {label}: nessun nodo selezionato")
                
        print("\n=== TEST COMPLETATO ===")
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_zone_selection()