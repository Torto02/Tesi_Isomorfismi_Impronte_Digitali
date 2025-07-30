import networkx as nx
import numpy as np
from matching import compute_complete_matching_score, is_direct_edge

# Test per verificare che il punteggio di un grafo con se stesso sia vicino a 1
def create_test_graph():
    G = nx.Graph()
    
    # Aggiungi nodi reali
    G.add_node(1, type='junction', pos=(0, 0))
    G.add_node(2, type='junction', pos=(1, 0))
    G.add_node(3, type='endpoint', pos=(0, 1))
    G.add_node(4, type='endpoint', pos=(1, 1))
    
    # Aggiungi archi diretti
    G.add_edge(1, 2)
    G.add_edge(3, 4)
    
    # Aggiungi un nodo 'added' e archi relativi
    G.add_node(5, type='added', pos=(0.5, 0.5))
    G.add_edge(1, 5)
    G.add_edge(5, 4, type='added')
    
    return G

# Crea due versioni del grafo per test (una leggermente diversa)
G_exact = create_test_graph()
G_similar = create_test_graph()
# Piccola variazione in G_similar
G_similar.nodes[3]['pos'] = (0, 1.02)  # Leggera variazione di posizione

# Calcola matrici di costo (usando distanza euclidea per semplicità)
def create_matrices(G):
    nodes = list(G.nodes())
    n = len(nodes)
    
    # Creiamo matrice di distanze
    M3 = {}
    for i in range(n):
        M3[nodes[i]] = {}
        for j in range(n):
            if i == j:
                M3[nodes[i]][nodes[j]] = 0
            elif 'pos' in G.nodes[nodes[i]] and 'pos' in G.nodes[nodes[j]]:
                pos_i = G.nodes[nodes[i]]['pos']
                pos_j = G.nodes[nodes[j]]['pos']
                dx = pos_i[0] - pos_j[0]
                dy = pos_i[1] - pos_j[1]
                M3[nodes[i]][nodes[j]] = (dx**2 + dy**2)**0.5
            else:
                M3[nodes[i]][nodes[j]] = float('inf')
    
    # Matrice degli scavalcamenti (per semplicità mettiamo 0 ovunque)
    M_scavalc = {}
    for i in range(n):
        M_scavalc[nodes[i]] = {}
        for j in range(n):
            M_scavalc[nodes[i]][nodes[j]] = 0
            
    return M3, M_scavalc

M3_exact, M_scavalc_exact = create_matrices(G_exact)
M3_similar, M_scavalc_similar = create_matrices(G_similar)

# Mapping identità (grafo con se stesso)
nodes = [n for n in G_exact.nodes() if G_exact.nodes[n].get('type') != 'added']
mapping_exact = {node: node for node in nodes}

# Test 1: Grafo identico a se stesso (dovrebbe dare 1.0)
score_exact, details_exact = compute_complete_matching_score(
    G_exact, G_exact, mapping_exact, M3_exact, M3_exact, M_scavalc_exact, M_scavalc_exact,
    cost_weight=1.0, angle_weight=2.0, edge_mode_weight=1.0,
    max_ridge_diff=1, cost_threshold_rel=0.5
)

print(f"Test 1 - Score del grafo con se stesso (ESATTO): {score_exact:.4f}")
print("Questo valore dovrebbe essere 1.0 per un match perfetto")

# Test 2: Grafo con piccola variazione (dovrebbe dare un punteggio alto ma < 1)
score_similar, details_similar = compute_complete_matching_score(
    G_exact, G_similar, mapping_exact, M3_exact, M3_similar, M_scavalc_exact, M_scavalc_similar,
    cost_weight=1.0, angle_weight=2.0, edge_mode_weight=1.0,
    max_ridge_diff=1, cost_threshold_rel=0.5
)

print(f"\nTest 2 - Score con grafo leggermente modificato: {score_similar:.4f}")
print("Questo valore dovrebbe essere alto ma < 1.0")

# Analizziamo i dettagli del test esatto
print("\n--- DETTAGLI TEST ESATTO ---")
for pair_id, details_pair in details_exact.items():
    print(f"\nDettagli per coppia {pair_id}:")
    for key, value in details_pair.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")

# Analizziamo i dettagli del test con variazione
print("\n--- DETTAGLI TEST CON VARIAZIONE ---")
for pair_id, details_pair in details_similar.items():
    print(f"\nDettagli per coppia {pair_id}:")
    for key, value in details_pair.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")