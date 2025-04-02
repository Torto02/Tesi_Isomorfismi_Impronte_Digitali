# import os
# import json
# import networkx as nx
# import math
# import matplotlib.pyplot as plt

# ##############################
# # 1) Definisci le funzioni per il matching
# ##############################

# def is_cost_similar(cA, cB, threshold=1):
#     if cA == float('inf') and cB == float('inf'):
#         return True
#     if cA == float('inf') or cB == float('inf'):
#         return False

#     denom = max(abs(cA), abs(cB), 1e-9)
#     diff = abs(cA - cB) / denom
#     return diff <= threshold

# def is_ridge_jump_similar(jumpA, jumpB, max_diff=2):
#     if jumpA == float('inf') and jumpB == float('inf'):
#         return True
#     if jumpA == float('inf') or jumpB == float('inf'):
#         return False
#     return abs(jumpA - jumpB) <= max_diff

# def match_subgraphs(
#     G_A, G_B,
#     M1_A, M2_A, M4_A,  # le matrici di A
#     M1_B, M2_B, M4_B,  # le matrici di B
#     nodeA, nodeB,
#     mapping=None,
#     visited_pairs=None,
#     cost_threshold=0.1,
#     max_ridge_diff=2
# ):
#     if mapping is None:
#         mapping = {}
#     if visited_pairs is None:
#         visited_pairs = set()

#     if (nodeA, nodeB) in visited_pairs:
#         return True
#     visited_pairs.add((nodeA, nodeB))

#     # 1) tipi di nodo uguali
#     if G_A.nodes[nodeA].get('type') != G_B.nodes[nodeB].get('type'):
#         return False

#     # 2) Aggiungiamo al mapping
#     if nodeA in mapping and mapping[nodeA] != nodeB:
#         return False
#     mapping[nodeA] = nodeB

#     # 3) DFS parallelo sui vicini
#     neighborsA = list(G_A[nodeA])
#     neighborsB = list(G_B[nodeB])

#     for nA in neighborsA:
#         found_match = False
#         for nB in neighborsB:
#             # già matchato?
#             if nB in mapping.values() and mapping.get(nA, None) != nB:
#                 continue

#             # check M1
#             if not is_cost_similar(M1_A[nodeA][nA], M1_B[nodeB][nB], cost_threshold):
#                 continue
#             # check M2
#             if not is_cost_similar(M2_A[nodeA][nA], M2_B[nodeB][nB], cost_threshold):
#                 continue
#             # check M4 (±2 salti)
#             if not is_ridge_jump_similar(M4_A[nodeA][nA], M4_B[nodeB][nB], max_ridge_diff):
#                 continue

#             # ricorsione
#             if match_subgraphs(G_A, G_B,
#                                M1_A, M2_A, M4_A,
#                                M1_B, M2_B, M4_B,
#                                nA, nB, mapping, visited_pairs,
#                                cost_threshold, max_ridge_diff):
#                 found_match = True
#                 break
#         if not found_match:
#             return False
#     return True

# ##############################
# # 2) Funzioni di supporto
# ##############################

# def single_source_custom_dijkstra(graph, source, weight_func):
#     for (u, v) in graph.edges():
#         d = graph[u][v]
#         d['temp_weight'] = weight_func(u, v, d)
#     distances = nx.single_source_dijkstra_path_length(graph, source, weight='temp_weight')
#     for (u, v) in graph.edges():
#         del graph[u][v]['temp_weight']
#     return distances

# def get_subgraph_within_radius(G, M3, source_node, radius):
#     N = G.number_of_nodes()
#     sub_nodes = [j for j in range(N) if M3[source_node][j] <= radius]
#     S = G.subgraph(sub_nodes).copy()
#     return S

# def plot_and_save_subgraph(S, G, source_node, output_folder, filename):
#     pos = nx.get_node_attributes(G, 'pos')
#     plt.figure(figsize=(8, 6))
#     nx.draw_networkx_nodes(S, pos, node_size=50, node_color="red")
#     nx.draw_networkx_edges(S, pos, edge_color="black", width=1)
#     if source_node in S:
#         nx.draw_networkx_nodes(S, pos, nodelist=[source_node],
#                                node_size=50, node_color="green")
#     nx.draw_networkx_labels(S, pos, labels={n: str(n) for n in S.nodes()},
#                             font_size=3, font_color="black")

#     plt.title(f"Sottografo attorno al nodo {source_node}")
#     plt.axis("off")

#     os.makedirs(output_folder, exist_ok=True)
#     output_path = os.path.join(output_folder, filename)
#     plt.savefig(output_path, dpi=600)
#     plt.close()
#     print(f"Immagine del sottografo salvata in: {output_path}")

# def save_matrix_to_file(matrix, filename):
#     with open(filename, 'w') as f:
#         for row in matrix:
#             f.write(','.join(map(str, row)) + '\n')

# def plot_mapping(S_A, S_B, G_A, G_B, mapping, output_folder, filename):
#     """
#     Visualizza il mapping tra due sottografi, mostrando le corrispondenze trovate.
#     """
#     fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
#     # Plot sottografo A
#     pos_A = nx.get_node_attributes(G_A, 'pos')
#     nx.draw_networkx_nodes(S_A, pos_A, node_size=50, node_color='lightblue', ax=ax1)
#     nx.draw_networkx_edges(S_A, pos_A, edge_color='gray', width=1, ax=ax1)
#     nx.draw_networkx_labels(S_A, pos_A, labels={n: str(n) for n in S_A.nodes()},
#                             font_size=8, font_color="black", ax=ax1)
    
#     # Evidenzia i nodi mappati in A
#     mapped_nodes_A = list(mapping.keys())
#     if mapped_nodes_A:
#         nx.draw_networkx_nodes(S_A, pos_A, nodelist=mapped_nodes_A,
#                                node_size=100, node_color='red', ax=ax1)
    
#     ax1.set_title("Sottografo A")
#     ax1.axis('off')
    
#     # Plot sottografo B
#     pos_B = nx.get_node_attributes(G_B, 'pos')
#     nx.draw_networkx_nodes(S_B, pos_B, node_size=50, node_color='lightblue', ax=ax2)
#     nx.draw_networkx_edges(S_B, pos_B, edge_color='gray', width=1, ax=ax2)
#     nx.draw_networkx_labels(S_B, pos_B, labels={n: str(n) for n in S_B.nodes()},
#                             font_size=8, font_color="black", ax=ax2)
    
#     # Evidenzia i nodi mappati in B
#     mapped_nodes_B = list(mapping.values())
#     if mapped_nodes_B:
#         nx.draw_networkx_nodes(S_B, pos_B, nodelist=mapped_nodes_B,
#                                node_size=100, node_color='red', ax=ax2)
    
#     ax2.set_title("Sottografo B")
#     ax2.axis('off')
    
#     plt.tight_layout()
    
#     # Salva l'immagine
#     os.makedirs(output_folder, exist_ok=True)
#     output_path = os.path.join(output_folder, filename)
#     plt.savefig(output_path, dpi=300, bbox_inches='tight')
#     plt.close()
    
#     print(f"Mapping visualizzato salvato in: {output_path}")

# ##############################
# # 3) Funzione per caricare una singola impronta e calcolare M1, M2, M3, M4
# ##############################

# def load_fingerprint_and_compute(folder_path):
#     """
#     Carica una singola impronta da folder_path, costruisce G,
#     calcola M1, M2, M3, M4 e SALVA le quattro matrici in /OutputMatrices/<nomeImpronta>.
#     Se le matrici esistono già, le carica direttamente senza ricalcolarle.
#     Ritorna (G, M1, M2, M3, M4).
#     """
#     # Carica i file JSON
#     nodes_file = os.path.join(folder_path, "nodes_graph.json")
#     edges_file = os.path.join(folder_path, "edges_graph.json")

#     if not os.path.exists(nodes_file) or not os.path.exists(edges_file):
#         print(f"Errore: File nodes_graph.json o edges_graph.json non trovati in {folder_path}.")
#         return None, None, None, None, None

#     # Verifica se le matrici esistono già
#     out_folder = "/Users/riccardotortorelli/Desktop/Tesi/OutputMatrices"
#     impronta_nome = os.path.basename(folder_path)
#     sub_folder = os.path.join(out_folder, impronta_nome)
    
#     m1_path = os.path.join(sub_folder, "M1.csv")
#     m2_path = os.path.join(sub_folder, "M2.csv")
#     m3_path = os.path.join(sub_folder, "M3.csv")
#     m4_path = os.path.join(sub_folder, "M4.csv")
    
#     # Costruisci il grafo in ogni caso (serve per il resto del programma)
#     with open(nodes_file, 'r') as f:
#         nodes_data = json.load(f)
#     with open(edges_file, 'r') as f:
#         edges_data = json.load(f)

#     nodes = nodes_data['nodes']
#     edges = edges_data['edges']

#     G = nx.Graph()
#     for i, node in enumerate(nodes):
#         coord = tuple(node.get('coordinates', [0, 0]))
#         ntype = node.get('type', 'unknown')
#         G.add_node(i, pos=coord, type=ntype)

#     for edge in edges:
#         node1, node2 = edge['nodes']
#         etype = edge.get('type', 'edge')
#         dist = edge.get('distance', None)
#         if node1 < len(nodes) and node2 < len(nodes):
#             G.add_edge(node1, node2, type=etype, distance=dist)
#         else:
#             print(f"Attenzione: arco con nodi {edge['nodes']} non valido.")
    
#     # Se tutte le matrici esistono, caricale
#     if os.path.exists(m1_path) and os.path.exists(m2_path) and os.path.exists(m3_path) and os.path.exists(m4_path):
#         print(f"\nMatrici già esistenti per {impronta_nome}, caricamento in corso...")
        
#         # Funzione per caricare una matrice da file CSV
#         def load_matrix_from_file(file_path):
#             matrix = []
#             with open(file_path, 'r') as f:
#                 for line in f:
#                     row = [float(val) if val != 'inf' else float('inf') for val in line.strip().split(',')]
#                     matrix.append(row)
#             return matrix
        
#         M1 = load_matrix_from_file(m1_path)
#         M2 = load_matrix_from_file(m2_path)
#         M3 = load_matrix_from_file(m3_path)
#         M4 = load_matrix_from_file(m4_path)
        
#         print(f"Matrici caricate con successo da: {sub_folder}")
#         return G, M1, M2, M3, M4
    
#     # Altrimenti, calcola le matrici
#     print(f"\nCalcolo delle matrici per {impronta_nome}...")
    
#     # Definizione delle 2 funzioni di peso
#     def weight_function_m1(u, v, d):
#         arco_type = d.get('type')
#         if arco_type == 'added':
#             return 1.0
#         elif arco_type == 'border':
#             return 5.0
#         else:
#             return 0.0001

#     def weight_function_m2(u, v, d):
#         if d.get('type') == 'added':
#             pos_u = G.nodes[u]['pos']
#             pos_v = G.nodes[v]['pos']
#             return math.dist(pos_u, pos_v)
#         else:
#             dist_attr = d.get('distance')
#             if dist_attr is not None:
#                 return dist_attr
#             else:
#                 pos_u = G.nodes[u]['pos']
#                 pos_v = G.nodes[v]['pos']
#                 return math.dist(pos_u, pos_v)

#     N = G.number_of_nodes()

#     # Calcolo M1
#     M1 = [[float('inf')] * N for _ in range(N)]
#     for node_start in G.nodes():
#         dist_dict = single_source_custom_dijkstra(G, node_start, weight_function_m1)
#         for node_end, dist_val in dist_dict.items():
#             M1[node_start][node_end] = dist_val

#     # Calcolo M2
#     M2 = [[float('inf')] * N for _ in range(N)]
#     for node_start in G.nodes():
#         dist_dict = single_source_custom_dijkstra(G, node_start, weight_function_m2)
#         for node_end, dist_val in dist_dict.items():
#             M2[node_start][node_end] = dist_val

#     # Calcolo M3
#     M3 = [[0.0] * N for _ in range(N)]
#     coords = [G.nodes[i]['pos'] for i in range(N)]
#     for i in range(N):
#         for j in range(N):
#             if i == j:
#                 M3[i][j] = 0.0
#             else:
#                 M3[i][j] = math.dist(coords[i], coords[j])

#     # Calcolo M4
#     M4 = [[float('inf')] * N for _ in range(N)]
#     for node_start in G.nodes():
#         dist_dict = nx.single_source_shortest_path_length(G, node_start)
#         for node_end, dist_val in dist_dict.items():
#             M4[node_start][node_end] = dist_val

#     # Salviamo le matrici
#     os.makedirs(sub_folder, exist_ok=True)
    
#     def save_matrix_to_file_local(matrix, filename):
#         with open(filename, 'w') as f:
#             for row in matrix:
#                 f.write(','.join(
#                     str(x) if x != float('inf') else 'inf' 
#                     for x in row
#                 ) + '\n')
    
#     save_matrix_to_file_local(M1, m1_path)
#     save_matrix_to_file_local(M2, m2_path)
#     save_matrix_to_file_local(M3, m3_path)
#     save_matrix_to_file_local(M4, m4_path)
    
#     print(f"M1, M2, M3, M4 salvate in: {sub_folder}")
#     return G, M1, M2, M3, M4

# ##############################
# # Funzione per ottenere i sotto-sottografi (4 minuzie)
# ##############################

# def get_connected_subgraphs_of_minutiae(S, size=4):
#     """
#     Genera tutti i sottografi connessi di S composti esclusivamente da 'size' minuzie 'vere',
#     escludendo dal calcolo della connettività gli archi di tipo 'added'.
#     Ritorna una lista di tuple (tuple_di_nodi, sottografo_indotto).
#     """
#     real_minutiae = [n for n in S.nodes() if S.nodes[n].get('type') in ('ending', 'bifurcation')]
#     S_no_added = S.copy()
#     edges_to_remove = [(u, v) for (u, v, data) in S.edges(data=True) if data.get('type') == 'added']
#     S_no_added.remove_edges_from(edges_to_remove)
    
#     S_minutiae = S_no_added.subgraph(real_minutiae).copy()
#     risultati = set()

#     def expand(current_set, candidates):
#         if len(current_set) == size:
#             risultati.add(frozenset(current_set))
#             return
#         for node in list(candidates):
#             new_current = current_set | {node}
#             new_candidates = (candidates | set(S_minutiae.neighbors(node))) - new_current
#             expand(new_current, new_candidates)
    
#     for node in S_minutiae.nodes():
#         expand({node}, set(S_minutiae.neighbors(node)))
    
#     subgraphs = [(tuple(sorted(list(s))), S_minutiae.subgraph(s).copy()) for s in risultati]
#     return subgraphs

# ##############################
# # 4) Funzione per stampare i grafi finali con i match in evidenza
# ##############################

# # def plot_final_graphs(G_A, G_B, 
# #                       matched_nodes_A, matched_nodes_B, 
# #                       centerA, radiusA, 
# #                       centerB, radiusB,
# #                       output_folder, filename):
# #     """
# #     Disegna i grafi G_A e G_B in nero, evidenziando in rosso i nodi e gli archi
# #     che fanno parte di almeno un match, e aggiunge una circonferenza colorata
# #     per mostrare l'area di ricerca in cui sono stati estratti i sotto-sottografi.
# #     Esclude gli archi di tipo 'added' dalla visualizzazione.
# #     """
# #     fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
    
# #     posA = nx.get_node_attributes(G_A, 'pos')
# #     posB = nx.get_node_attributes(G_B, 'pos')
    
# #     # Filtro gli archi 'added' dal grafo A
# #     edges_A_no_added = [(u, v) for (u, v, data) in G_A.edges(data=True) 
# #                         if data.get('type') != 'added']
    
# #     # 1) GRAFO A
# #     non_matched_nodes_A = [n for n in G_A.nodes() if n not in matched_nodes_A]
# #     non_matched_edges_A = [
# #         (u, v) for (u, v) in edges_A_no_added 
# #         if (u not in matched_nodes_A) or (v not in matched_nodes_A)
# #     ]
    
# #     # Nodi e archi NON matchati (in nero)
# #     nx.draw_networkx_nodes(G_A, posA, nodelist=non_matched_nodes_A, 
# #                            node_size=0.01, node_color='black', ax=ax1)
# #     nx.draw_networkx_edges(G_A, posA, edgelist=non_matched_edges_A, 
# #                            edge_color='gray', width=0.1, ax=ax1)
    
# #     # Nodi e archi matchati (in rosso)
# #     matched_edges_A = [(u, v) for (u, v) in edges_A_no_added
# #                        if (u in matched_nodes_A) and (v in matched_nodes_A)]
# #     nx.draw_networkx_nodes(G_A, posA, nodelist=list(matched_nodes_A), 
# #                            node_size=0.01, node_color='red', ax=ax1)
# #     nx.draw_networkx_edges(G_A, posA, edgelist=matched_edges_A,
# #                            edge_color='red', width=0.1, ax=ax1)
    
# #     # Disegno la circonferenza che mostra l'area di ricerca in G_A
# #     if centerA is not None and radiusA is not None:
# #         circleA = Circle(centerA, radiusA, fill=False, edgecolor='blue', linewidth=1)
# #         ax1.add_patch(circleA)
    
# #     ax1.set_title("Grafo A (match in rosso)")
# #     ax1.axis('off')
# #     ax1.set_aspect('equal', adjustable='datalim')
    
# #     # Filtro gli archi 'added' dal grafo B
# #     edges_B_no_added = [(u, v) for (u, v, data) in G_B.edges(data=True) 
# #                         if data.get('type') != 'added']
    
# #     # 2) GRAFO B
# #     non_matched_nodes_B = [n for n in G_B.nodes() if n not in matched_nodes_B]
# #     non_matched_edges_B = [
# #         (u, v) for (u, v) in edges_B_no_added 
# #         if (u not in matched_nodes_B) or (v not in matched_nodes_B)
# #     ]
    
# #     # Nodi e archi NON matchati (in nero)
# #     nx.draw_networkx_nodes(G_B, posB, nodelist=non_matched_nodes_B, 
# #                            node_size=0.01, node_color='black', ax=ax2)
# #     nx.draw_networkx_edges(G_B, posB, edgelist=non_matched_edges_B, 
# #                            edge_color='black', width=0.1, ax=ax2)
    
# #     # Nodi e archi matchati (in rosso)
# #     matched_edges_B = [(u, v) for (u, v) in edges_B_no_added
# #                        if (u in matched_nodes_B) and (v in matched_nodes_B)]
# #     nx.draw_networkx_nodes(G_B, posB, nodelist=list(matched_nodes_B), 
# #                            node_size=0.01, node_color='red', ax=ax2)
# #     nx.draw_networkx_edges(G_B, posB, edgelist=matched_edges_B,
# #                            edge_color='red', width=0.1, ax=ax2)
    
# #     # Disegno la circonferenza che mostra l'area di ricerca in G_B
# #     if centerB is not None and radiusB is not None:
# #         circleB = Circle(centerB, radiusB, fill=False, edgecolor='blue', linewidth=1)
# #         ax2.add_patch(circleB)
    
# #     ax2.set_title("Grafo B (match in rosso)")
# #     ax2.axis('off')
# #     ax2.set_aspect('equal', adjustable='datalim')
    
# #     plt.tight_layout()
    
# #     os.makedirs(output_folder, exist_ok=True)
# #     out_path = os.path.join(output_folder, filename)
# #     plt.savefig(out_path, dpi=1000)
# #     plt.close()
    
# #     print(f"Stampa finale dei grafi salvata in: {out_path}")


# import matplotlib.pyplot as plt
# from matplotlib.patches import Circle

# def plot_final_graphs(G_A, G_B, 
#                       matched_nodes_A, matched_nodes_B, 
#                       centerA, radiusA, 
#                       centerB, radiusB,
#                       output_folder, filename):
#     """
#     Disegna i grafi G_A e G_B in nero, evidenziando in rosso i nodi e gli archi
#     che fanno parte di almeno un match, e aggiunge una circonferenza colorata
#     per mostrare l'area di ricerca in cui sono stati estratti i sotto-sottografi.
    
#     Parametri:
#     -----------
#     - G_A, G_B : i due grafi originali
#     - matched_nodes_A, matched_nodes_B : set di nodi mappati almeno in un match
#     - centerA, radiusA : centro (tupla x,y) e raggio della circonferenza per A
#     - centerB, radiusB : centro (tupla x,y) e raggio della circonferenza per B
#     - output_folder, filename : per salvare l'immagine risultante
#     """
#     fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
    
#     posA = nx.get_node_attributes(G_A, 'pos')
#     posB = nx.get_node_attributes(G_B, 'pos')
    
#     # 1) GRAFO A
#     non_matched_nodes_A = [n for n in G_A.nodes() if n not in matched_nodes_A]
#     non_matched_edges_A = [
#         (u, v) for (u, v) in G_A.edges() 
#         if (u not in matched_nodes_A) or (v not in matched_nodes_A)
#     ]
    
#     # Nodi e archi NON matchati (in nero)
#     nx.draw_networkx_nodes(G_A, posA, nodelist=non_matched_nodes_A, 
#                            node_size=0.1, node_color='black', ax=ax1)
#     nx.draw_networkx_edges(G_A, posA, edgelist=non_matched_edges_A, 
#                            edge_color='gray', width=0.1, ax=ax1)
    
#     # Nodi e archi matchati (in rosso)
#     matched_edges_A = [(u, v) for (u, v) in G_A.edges()
#                        if (u in matched_nodes_A) and (v in matched_nodes_A)]
#     nx.draw_networkx_nodes(G_A, posA, nodelist=list(matched_nodes_A), 
#                            node_size=0.1, node_color='red', ax=ax1)
#     nx.draw_networkx_edges(G_A, posA, edgelist=matched_edges_A,
#                            edge_color='red', width=0.1, ax=ax1)
    
#     # Disegno la circonferenza che mostra l'area di ricerca in G_A
#     if centerA is not None and radiusA is not None:
#         circleA = Circle(centerA, radiusA, fill=False, edgecolor='blue', linewidth=1)
#         ax1.add_patch(circleA)
    
#     ax1.set_title("Grafo A (match in rosso)")
#     ax1.axis('off')
#     ax1.set_aspect('equal', adjustable='datalim')
    
#     # 2) GRAFO B
#     non_matched_nodes_B = [n for n in G_B.nodes() if n not in matched_nodes_B]
#     non_matched_edges_B = [
#         (u, v) for (u, v) in G_B.edges() 
#         if (u not in matched_nodes_B) or (v not in matched_nodes_B)
#     ]
    
#     # Nodi e archi NON matchati (in nero)
#     nx.draw_networkx_nodes(G_B, posB, nodelist=non_matched_nodes_B, 
#                            node_size=0.1, node_color='black', ax=ax2)
#     nx.draw_networkx_edges(G_B, posB, edgelist=non_matched_edges_B, 
#                            edge_color='black', width=0.1, ax=ax2)
    
#     # Nodi e archi matchati (in rosso)
#     matched_edges_B = [(u, v) for (u, v) in G_B.edges()
#                        if (u in matched_nodes_B) and (v in matched_nodes_B)]
#     nx.draw_networkx_nodes(G_B, posB, nodelist=list(matched_nodes_B), 
#                            node_size=0.1, node_color='red', ax=ax2)
#     nx.draw_networkx_edges(G_B, posB, edgelist=matched_edges_B,
#                            edge_color='red', width=0.1, ax=ax2)
    
#     # Disegno la circonferenza che mostra l'area di ricerca in G_B
#     if centerB is not None and radiusB is not None:
#         circleB = Circle(centerB, radiusB, fill=False, edgecolor='blue', linewidth=1)
#         ax2.add_patch(circleB)
    
#     ax2.set_title("Grafo B (match in rosso)")
#     ax2.axis('off')
#     ax2.set_aspect('equal', adjustable='datalim')
    
#     plt.tight_layout()
    
#     os.makedirs(output_folder, exist_ok=True)
#     out_path = os.path.join(output_folder, filename)
#     plt.savefig(out_path, dpi=1000)
#     plt.close()
    
#     print(f"Stampa finale dei grafi salvata in: {out_path}")



# ##############################
# # 5) Funzione principale (main)
# ##############################

# def main():
#     base_folder = "/Users/riccardotortorelli/Desktop/Tesi/Archivio"
#     if not os.path.exists(base_folder):
#         print("Errore: La cartella specificata non esiste.")
#         return

#     # Carica 2 impronte
#     impronte_disponibili = sorted([d for d in os.listdir(base_folder)
#                                    if os.path.isdir(os.path.join(base_folder, d))])
#     if len(impronte_disponibili) < 2:
#         print("Servono almeno 2 impronte nella cartella.")
#         return

#     # Scegli impronta A
#     print("\nImpronte disponibili:")
#     for idx, nome in enumerate(impronte_disponibili):
#         print(f"{idx + 1}. {nome}")

#     while True:
#         try:
#             sceltaA = int(input("\nSeleziona il numero dell'impronta A: ")) - 1
#             if 0 <= sceltaA < len(impronte_disponibili):
#                 improntaA_selezionata = impronte_disponibili[sceltaA]
#                 break
#             else:
#                 print("Selezione non valida per A.")
#         except ValueError:
#             print("Errore: inserisci un numero valido.")

#     folder_A = os.path.join(base_folder, improntaA_selezionata)
#     G_A, M1_A, M2_A, M3_A, M4_A = load_fingerprint_and_compute(folder_A)
#     if G_A is None:
#         print("Impossibile caricare impronta A.")
#         return

#     # Scegli impronta B
#     while True:
#         try:
#             sceltaB = int(input("\nSeleziona il numero dell'impronta B: ")) - 1
#             if 0 <= sceltaB < len(impronte_disponibili):
#                 improntaB_selezionata = impronte_disponibili[sceltaB]
#                 break
#             else:
#                 print("Selezione non valida per B.")
#         except ValueError:
#             print("Errore: inserisci un numero valido.")

#     folder_B = os.path.join(base_folder, improntaB_selezionata)
#     G_B, M1_B, M2_B, M3_B, M4_B = load_fingerprint_and_compute(folder_B)
#     if G_B is None:
#         print("Impossibile caricare impronta B.")
#         return

#     print(f"\nImpronta A = {improntaA_selezionata}, #nodi={G_A.number_of_nodes()}, #archi={G_A.number_of_edges()}")
#     print(f"Impronta B = {improntaB_selezionata}, #nodi={G_B.number_of_nodes()}, #archi={G_B.number_of_edges()}")

#     # Scelta minuzia in A
#     minutia_nodesA = [n for n in G_A.nodes() if G_A.nodes[n]['type'] in ('ending','bifurcation')]
#     if not minutia_nodesA:
#         print("Nessuna minuzia trovata in A.")
#         return
#     print(f"\nMinuzie disponibili in {improntaA_selezionata}:")
#     for idx, node_id in enumerate(minutia_nodesA):
#         node_type = G_A.nodes[node_id]['type']
#         node_pos = G_A.nodes[node_id]['pos']
#         print(f"{idx + 1}. Nodo {node_id} - Tipo: {node_type}, Posizione: {node_pos}")
    
#     while True:
#         try:
#             minutia_idx = int(input(f"\nSeleziona il numero della minuzia per {improntaA_selezionata} (1-{len(minutia_nodesA)}): ")) - 1
#             if 0 <= minutia_idx < len(minutia_nodesA):
#                 minuziaA = minutia_nodesA[minutia_idx]
#                 print(f"Hai selezionato il nodo {minuziaA} di tipo {G_A.nodes[minuziaA]['type']}")
#                 break
#             else:
#                 print(f"Selezione non valida. Inserisci un numero tra 1 e {len(minutia_nodesA)}.")
#         except ValueError:
#             print("Errore: inserisci un numero valido.")
    
#     max_dist_A = max(max(row) for row in M3_A if max(row) < float('inf'))
#     radiusA = 0.1 * max_dist_A
#     S_A = get_subgraph_within_radius(G_A, M3_A, minuziaA, radiusA)
#     print(f"Sottografo S_A con raggio={radiusA:.2f}, nodi={S_A.number_of_nodes()}, archi={S_A.number_of_edges()}")
    
#     out_graphs = "/Users/riccardotortorelli/Desktop/Tesi/OutputGraph"
#     os.makedirs(out_graphs, exist_ok=True)
#     plot_and_save_subgraph(S_A, G_A, minuziaA, out_graphs, 
#                            f"macro_subgraph_A_{improntaA_selezionata}_nodo{minuziaA}.png")

#     # Selezione automatica minuzia in B più vicina
#     minutia_nodesB = [n for n in G_B.nodes() if G_B.nodes[n]['type'] in ('ending','bifurcation')]
#     if not minutia_nodesB:
#         print("Nessuna minuzia trovata in B.")
#         return
    
#     posA = G_A.nodes[minuziaA]['pos']
#     closest_minutiaB = None
#     min_distance = float('inf')
#     for node_id in minutia_nodesB:
#         posB = G_B.nodes[node_id]['pos']
#         distance = math.dist(posA, posB)
#         if distance < min_distance:
#             min_distance = distance
#             closest_minutiaB = node_id
    
#     minuziaB = closest_minutiaB
#     print(f"\nMinuzia più vicina in {improntaB_selezionata}: nodo {minuziaB} (distanza = {min_distance:.2f})")

#     max_dist_B = max(max(row) for row in M3_B if max(row) < float('inf'))
#     radiusB = 0.17 * max_dist_B
#     S_B = get_subgraph_within_radius(G_B, M3_B, minuziaB, radiusB)
#     print(f"Sottografo S_B con raggio={radiusB:.2f}, nodi={S_B.number_of_nodes()}, archi={S_B.number_of_edges()}")

#     plot_and_save_subgraph(S_B, G_B, minuziaB, out_graphs, 
#                            f"macro_subgraph_B_{improntaB_selezionata}_nodo{minuziaB}.png")

#     # -------------- MATCH SUI SOTTO-SOTTOGRAFI ---------------
#     sub_subgraphs_A = get_connected_subgraphs_of_minutiae(S_A, size=4)
#     sub_subgraphs_B = get_connected_subgraphs_of_minutiae(S_B, size=4)

#     print(f"\nIn S_A abbiamo {len(sub_subgraphs_A)} sotto-sottografi (4 minuzie).")
#     print(f"In S_B abbiamo {len(sub_subgraphs_B)} sotto-sottografi (4 minuzie).")

#     out_subgraphs = "/Users/riccardotortorelli/Desktop/Tesi/OutputSubgraphs"
#     os.makedirs(out_subgraphs, exist_ok=True)

#     match_counter = 0

#     # Per la stampa finale, accumuliamo tutti i nodi matchati in questi set
#     matched_nodes_A = set()
#     matched_nodes_B = set()

#     for (subsetA, subG_A) in sub_subgraphs_A:
#         for (subsetB, subG_B) in sub_subgraphs_B:
#             if not subsetA or not subsetB:
#                 continue
#             nodeA = list(subsetA)[0]
#             nodeB = list(subsetB)[0]

#             mapping = {}
#             success = match_subgraphs(
#                 subG_A, subG_B,
#                 M1_A, M2_A, M4_A,
#                 M1_B, M2_B, M4_B,
#                 nodeA, nodeB,
#                 mapping=mapping,
#                 cost_threshold=0.05,
#                 max_ridge_diff=2
#             )
#             if success and len(mapping) == len(subG_A.nodes()):
#                 match_counter += 1
#                 print(f"\nTrovato match #{match_counter}!")
#                 print(f"Nodi in subG_A: {subsetA}, Nodi in subG_B: {subsetB}")
#                 print("Mapping:", mapping)

#                 # Aggiungiamo i nodi matchati nei set globali
#                 matched_nodes_A.update(mapping.keys())
#                 matched_nodes_B.update(mapping.values())

#                 # Plot del singolo match (opzionale)
#                 plot_mapping(subG_A, subG_B, G_A, G_B, mapping,
#                              out_subgraphs,
#                              f"match_{nodeA}_{nodeB}.png")

#     print(f"\nTotale match trovati = {match_counter}")

#     # Stampa finale dei due grafi completi con i match in evidenza
#     # plot_final_graphs(G_A, G_B, matched_nodes_A, matched_nodes_B, 
#     #                   out_graphs, "final_matches_A_B.png")
#     # ...
# # Alla fine del main (dopo aver trovato i match), richiama la stampa finale
#     plot_final_graphs(
#         G_A, 
#         G_B,
#         matched_nodes_A,
#         matched_nodes_B,
#         centerA = G_A.nodes[minuziaA]['pos'],  # posizione (x,y) del nodo sorgente in A
#         radiusA = radiusA,                     # raggio usato per S_A
#         centerB = G_B.nodes[minuziaB]['pos'],  # posizione (x,y) del nodo sorgente in B
#         radiusB = radiusB,                     # raggio usato per S_B
#         output_folder = out_graphs,
#         filename = "final_matches_A_B.png"
#     )


#     print("\n--- Elaborazione completata ---")

# if __name__ == "__main__":
#     main()


import os
import json
import networkx as nx
import math
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

##############################
# 1) Definisci le funzioni per il matching
##############################

def is_cost_similar(cA, cB, threshold=1.5):
    """
    Verifica se due costi (M1 o M2) sono abbastanza simili in valore relativo.
    """
    if cA == float('inf') and cB == float('inf'):
        return True
    if cA == float('inf') or cB == float('inf'):
        return False

    denom = max(abs(cA), abs(cB), 1e-9)
    diff = abs(cA - cB) / denom
    return diff <= threshold

def is_ridge_jump_similar(jumpA, jumpB, max_diff=2):
    """
    Verifica se la differenza in M4 (numero di salti/ridge jumps) è sotto una soglia.
    """
    if jumpA == float('inf') and jumpB == float('inf'):
        return True
    if jumpA == float('inf') or jumpB == float('inf'):
        return False
    return abs(jumpA - jumpB) <= max_diff

def match_subgraphs(
    G_A, G_B,
    M1_A, M2_A, M4_A,  # Matrici di A
    M1_B, M2_B, M4_B,  # Matrici di B
    nodeA, nodeB,
    mapping=None,
    visited_pairs=None,
    cost_threshold=0.1,
    max_ridge_diff=2
):
    """
    Tenta di effettuare il match (allineamento) ricorsivo di due sottografi G_A e G_B,
    partendo da nodeA e nodeB. Verifica:
      1) Tipo di nodo.
      2) Similitudine costi (M1, M2) e differenza salti (M4).
      3) Ricorsione sui vicini.
    
    Nota importante:
    In questo matching, ogni volta che esaminiamo "neighborsA = G_A[nodeA]" 
    e "neighborsB = G_B[nodeB]", stiamo effettivamente controllando 
    *tutti gli archi reali* fra i nodi del sottografo, non solo quelli 
    derivati da una BFS o simili. Quindi la risposta al dubbio del professore 
    è: verifichiamo effettivamente tutti gli archi possibili 
    (che esistono in G_A e G_B).
    """

    if mapping is None:
        mapping = {}
    if visited_pairs is None:
        visited_pairs = set()

    if (nodeA, nodeB) in visited_pairs:
        return True
    visited_pairs.add((nodeA, nodeB))

    # 1) tipi di nodo uguali
    if G_A.nodes[nodeA].get('type') != G_B.nodes[nodeB].get('type'):
        return False

    # 2) Aggiungiamo al mapping
    if nodeA in mapping and mapping[nodeA] != nodeB:
        return False
    mapping[nodeA] = nodeB

    # 3) DFS parallelo sui vicini (verificando M1, M2, M4)
    neighborsA = list(G_A[nodeA])
    neighborsB = list(G_B[nodeB])

    for nA in neighborsA:
        found_match = False
        for nB in neighborsB:
            # già matchato?
            if nB in mapping.values() and mapping.get(nA, None) != nB:
                continue

            # check M1
            if not is_cost_similar(M1_A[nodeA][nA], M1_B[nodeB][nB], cost_threshold):
                continue
            # check M2
            if not is_cost_similar(M2_A[nodeA][nA], M2_B[nodeB][nB], cost_threshold):
                continue
            # check M4 (±2 salti)
            if not is_ridge_jump_similar(M4_A[nodeA][nA], M4_B[nodeB][nB], max_ridge_diff):
                continue

            # ricorsione
            if match_subgraphs(
                G_A, G_B,
                M1_A, M2_A, M4_A,
                M1_B, M2_B, M4_B,
                nA, nB, mapping, visited_pairs,
                cost_threshold, max_ridge_diff
            ):
                found_match = True
                break
        if not found_match:
            return False
    return True


##############################
# 2) Funzioni di supporto
##############################

def single_source_custom_dijkstra(graph, source, weight_func):
    """
    Esegue una dijkstra personalizzata su 'graph' a partire da 'source',
    usando 'weight_func' come funzione per calcolare il peso di ogni arco.
    Ritorna un dizionario {nodo_destinazione: distanza}.
    """
    # Aggiunge la chiave 'temp_weight' ai singoli archi per lanciare la dijkstra nativa di networkx.
    for (u, v) in graph.edges():
        d = graph[u][v]
        d['temp_weight'] = weight_func(u, v, d)
    distances = nx.single_source_dijkstra_path_length(graph, source, weight='temp_weight')
    # Ripulisce la chiave 'temp_weight'
    for (u, v) in graph.edges():
        del graph[u][v]['temp_weight']
    return distances

def get_subgraph_within_radius(G, M3, source_node, radius):
    """
    Ritorna il sottografo di G contenente i nodi che distano <= radius dal source_node
    in base alla matrice M3 (che contiene le distanze euclidee).
    """
    N = G.number_of_nodes()
    sub_nodes = [j for j in range(N) if M3[source_node][j] <= radius]
    S = G.subgraph(sub_nodes).copy()
    return S

def plot_and_save_subgraph(S, G, source_node, output_folder, filename):
    """
    Disegna il sottografo S (estratto da G) e lo salva.
    - Disegna solo archi non 'added'.
    - I nodi vengono colorati in base al loro 'type'.
    - Sorgente evidenziata in un altro colore.
    """
    pos = nx.get_node_attributes(G, 'pos')
    
    # Filtra archi "veri ridge"
    true_ridge_edges = [(u, v) for (u, v, data) in S.edges(data=True)
                        if data.get('type') != 'added']

    # Mappa colori per i tipi di nodo
    color_map = {
        'ending': 'red',
        'bifurcation': 'blue',
        'core': 'green',
        'delta': 'orange'
    }

    # Costruisco la lista di colori corrispondente all'ordine dei nodi in S
    node_colors = []
    for n in S.nodes():
        tipo = S.nodes[n].get('type', 'unknown')
        node_colors.append(color_map.get(tipo, 'black'))  # default 'black' se non trovato

    plt.figure(figsize=(8, 6))

    # Disegno i nodi con colore a seconda del tipo
    nx.draw_networkx_nodes(
        S, pos,
        node_size=50,
        node_color=node_colors
    )
    # Disegno solo gli archi "veri ridge"
    nx.draw_networkx_edges(
        S, pos,
        edgelist=true_ridge_edges,
        edge_color="black",
        width=1
    )

    # Evidenzio il nodo sorgente (se presente)
    if source_node in S:
        nx.draw_networkx_nodes(
            S, pos,
            nodelist=[source_node],
            node_size=80,
            node_color="yellow"
        )

    # Label sui nodi
    nx.draw_networkx_labels(
        S, pos,
        labels={n: str(n) for n in S.nodes()},
        font_size=3,
        font_color="black"
    )

    plt.title(f"Sottografo attorno al nodo {source_node}")
    plt.axis("off")

    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, filename)
    plt.savefig(output_path, dpi=600)
    plt.close()
    print(f"Immagine del sottografo salvata in: {output_path}")

def save_matrix_to_file(matrix, filename):
    """
    Salva una matrice su file CSV.
    """
    with open(filename, 'w') as f:
        for row in matrix:
            f.write(','.join(map(str, row)) + '\n')


def plot_mapping(S_A, S_B, G_A, G_B, mapping, output_folder, filename):
    """
    Visualizza il mapping tra due sottografi, mostrando le corrispondenze trovate.
    - Disegno i due sottografi uno di fianco all'altro.
    - Evidenzio in rosso i nodi mappati.
    - Disegno solo gli archi non 'added'.
    - Uso colori diversi per i nodi (a seconda del loro tipo).
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    pos_A = nx.get_node_attributes(G_A, 'pos')
    pos_B = nx.get_node_attributes(G_B, 'pos')

    # Filtriamo archi "veri ridge" in S_A
    true_ridge_edges_A = [(u, v) for (u, v, data) in S_A.edges(data=True)
                          if data.get('type') != 'added']

    # Mappa colori per i tipi di nodo (uguale a quella usata altrove)
    color_map = {
        'ending': 'red',
        'bifurcation': 'blue',
        'core': 'green',
        'delta': 'orange'
    }
    # Costruisco la lista di colori per S_A
    node_colors_A = []
    for n in S_A.nodes():
        t = S_A.nodes[n].get('type', 'unknown')
        node_colors_A.append(color_map.get(t, 'black'))

    # Plot sottografo A
    nx.draw_networkx_nodes(
        S_A, pos_A,
        node_size=50,
        node_color=node_colors_A,
        ax=ax1
    )
    nx.draw_networkx_edges(
        S_A, pos_A,
        edgelist=true_ridge_edges_A,
        edge_color='gray',
        width=1,
        ax=ax1
    )
    nx.draw_networkx_labels(
        S_A, pos_A,
        labels={n: str(n) for n in S_A.nodes()},
        font_size=8,
        font_color="black",
        ax=ax1
    )
    
    # Evidenzia i nodi mappati in A
    mapped_nodes_A = list(mapping.keys())
    if mapped_nodes_A:
        nx.draw_networkx_nodes(
            S_A, pos_A,
            nodelist=mapped_nodes_A,
            node_size=100,
            node_color='red',
            ax=ax1
        )
    
    ax1.set_title("Sottografo A")
    ax1.axis('off')
    
    # Filtriamo archi "veri ridge" in S_B
    true_ridge_edges_B = [(u, v) for (u, v, data) in S_B.edges(data=True)
                          if data.get('type') != 'added']

    # Costruisco la lista di colori per S_B
    node_colors_B = []
    for n in S_B.nodes():
        t = S_B.nodes[n].get('type', 'unknown')
        node_colors_B.append(color_map.get(t, 'black'))

    # Plot sottografo B
    nx.draw_networkx_nodes(
        S_B, pos_B,
        node_size=50,
        node_color=node_colors_B,
        ax=ax2
    )
    nx.draw_networkx_edges(
        S_B, pos_B,
        edgelist=true_ridge_edges_B,
        edge_color='gray',
        width=1,
        ax=ax2
    )
    nx.draw_networkx_labels(
        S_B, pos_B,
        labels={n: str(n) for n in S_B.nodes()},
        font_size=8,
        font_color="black",
        ax=ax2
    )
    
    # Evidenzia i nodi mappati in B
    mapped_nodes_B = list(mapping.values())
    if mapped_nodes_B:
        nx.draw_networkx_nodes(
            S_B, pos_B,
            nodelist=mapped_nodes_B,
            node_size=100,
            node_color='red',
            ax=ax2
        )
    
    ax2.set_title("Sottografo B")
    ax2.axis('off')
    
    plt.tight_layout()
    
    # Salva l'immagine
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, filename)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Mapping visualizzato salvato in: {output_path}")

##############################
# 3) Funzione per caricare una singola impronta e calcolare M1, M2, M3, M4
##############################

def load_fingerprint_and_compute(folder_path):
    """
    Carica una singola impronta da folder_path, costruisce G,
    calcola (o ricarica da file) M1, M2, M3, M4.
    Ritorna (G, M1, M2, M3, M4).
    """
    # Carica i file JSON
    nodes_file = os.path.join(folder_path, "nodes_graph.json")
    edges_file = os.path.join(folder_path, "edges_graph.json")

    if not os.path.exists(nodes_file) or not os.path.exists(edges_file):
        print(f"Errore: File nodes_graph.json o edges_graph.json non trovati in {folder_path}.")
        return None, None, None, None, None

    # Cartella di output per le matrici
    out_folder = "/Users/riccardotortorelli/Desktop/Tesi/OutputMatrices"
    impronta_nome = os.path.basename(folder_path)
    sub_folder = os.path.join(out_folder, impronta_nome)
    
    m1_path = os.path.join(sub_folder, "M1.csv")
    m2_path = os.path.join(sub_folder, "M2.csv")
    m3_path = os.path.join(sub_folder, "M3.csv")
    m4_path = os.path.join(sub_folder, "M4.csv")
    
    # Costruisci comunque il grafo G
    with open(nodes_file, 'r') as f:
        nodes_data = json.load(f)
    with open(edges_file, 'r') as f:
        edges_data = json.load(f)

    nodes = nodes_data['nodes']
    edges = edges_data['edges']

    G = nx.Graph()
    for i, node in enumerate(nodes):
        coord = tuple(node.get('coordinates', [0, 0]))
        ntype = node.get('type', 'unknown')
        G.add_node(i, pos=coord, type=ntype)

    for edge in edges:
        node1, node2 = edge['nodes']
        etype = edge.get('type', 'edge')
        dist = edge.get('distance', None)
        if node1 < len(nodes) and node2 < len(nodes):
            G.add_edge(node1, node2, type=etype, distance=dist)
        else:
            print(f"Attenzione: arco con nodi {edge['nodes']} non valido.")
    
    # Se le matrici esistono già, le carichiamo
    if (os.path.exists(m1_path) and os.path.exists(m2_path) and
        os.path.exists(m3_path) and os.path.exists(m4_path)):
        print(f"\nMatrici già esistenti per {impronta_nome}, caricamento in corso...")
        
        def load_matrix_from_file(file_path):
            matrix = []
            with open(file_path, 'r') as f:
                for line in f:
                    row = [float(val) if val != 'inf' else float('inf')
                           for val in line.strip().split(',')]
                    matrix.append(row)
            return matrix
        
        M1 = load_matrix_from_file(m1_path)
        M2 = load_matrix_from_file(m2_path)
        M3 = load_matrix_from_file(m3_path)
        M4 = load_matrix_from_file(m4_path)
        
        print(f"Matrici caricate con successo da: {sub_folder}")
        return G, M1, M2, M3, M4
    
    # Altrimenti, le calcoliamo da zero
    print(f"\nCalcolo delle matrici per {impronta_nome}...")
    
    # Definizione delle 2 funzioni di peso
    def weight_function_m1(u, v, d):
        arco_type = d.get('type')
        if arco_type == 'added':
            return 1.0
        elif arco_type == 'border':
            return 5.0
        else:
            return 0.0001

    def weight_function_m2(u, v, d):
        if d.get('type') == 'added':
            pos_u = G.nodes[u]['pos']
            pos_v = G.nodes[v]['pos']
            return math.dist(pos_u, pos_v)
        else:
            dist_attr = d.get('distance')
            if dist_attr is not None:
                return dist_attr
            else:
                # fallback: distanza euclidea tra posizioni
                pos_u = G.nodes[u]['pos']
                pos_v = G.nodes[v]['pos']
                return math.dist(pos_u, pos_v)

    N = G.number_of_nodes()

    # Calcolo M1
    M1 = [[float('inf')] * N for _ in range(N)]
    for node_start in G.nodes():
        dist_dict = single_source_custom_dijkstra(G, node_start, weight_function_m1)
        for node_end, dist_val in dist_dict.items():
            M1[node_start][node_end] = dist_val

    # Calcolo M2
    M2 = [[float('inf')] * N for _ in range(N)]
    for node_start in G.nodes():
        dist_dict = single_source_custom_dijkstra(G, node_start, weight_function_m2)
        for node_end, dist_val in dist_dict.items():
            M2[node_start][node_end] = dist_val

    # Calcolo M3 (euclidea pura)
    M3 = [[0.0] * N for _ in range(N)]
    coords = [G.nodes[i]['pos'] for i in range(N)]
    for i in range(N):
        for j in range(N):
            if i == j:
                M3[i][j] = 0.0
            else:
                M3[i][j] = math.dist(coords[i], coords[j])

    # Calcolo M4 (numero di salti, BFS)
    M4 = [[float('inf')] * N for _ in range(N)]
    for node_start in G.nodes():
        dist_dict = nx.single_source_shortest_path_length(G, node_start)
        for node_end, dist_val in dist_dict.items():
            M4[node_start][node_end] = dist_val

    # Salviamo le matrici
    os.makedirs(sub_folder, exist_ok=True)
    
    def save_matrix_to_file_local(matrix, filename):
        with open(filename, 'w') as f:
            for row in matrix:
                f.write(','.join(
                    str(x) if x != float('inf') else 'inf'
                    for x in row
                ) + '\n')
    
    save_matrix_to_file_local(M1, m1_path)
    save_matrix_to_file_local(M2, m2_path)
    save_matrix_to_file_local(M3, m3_path)
    save_matrix_to_file_local(M4, m4_path)
    
    print(f"M1, M2, M3, M4 salvate in: {sub_folder}")
    return G, M1, M2, M3, M4

##############################
# Funzione per ottenere i sottografi connessi di minuzie (5 nodi)
##############################

def get_connected_subgraphs_of_minutiae(S, size=5):
    """
    Genera tutti i sottografi connessi di S composti esclusivamente da 'size' minuzie 'vere',
    escludendo dal calcolo della connettività gli archi di tipo 'added'.
    Ritorna una lista di tuple (tuple_di_nodi, sottografo_indotto).
    
    N.B. Se vuoi 6, basta cambiare size=6 o rendere la funzione parametrica.
    """
    real_minutiae = [n for n in S.nodes() if S.nodes[n].get('type') in ('ending', 'bifurcation')]
    S_no_added = S.copy()
    edges_to_remove = [(u, v) for (u, v, data) in S.edges(data=True) if data.get('type') == 'added']
    S_no_added.remove_edges_from(edges_to_remove)
    
    S_minutiae = S_no_added.subgraph(real_minutiae).copy()
    risultati = set()

    def expand(current_set, candidates):
        if len(current_set) == size:
            risultati.add(frozenset(current_set))
            return
        for node in list(candidates):
            new_current = current_set | {node}
            new_candidates = (candidates | set(S_minutiae.neighbors(node))) - new_current
            expand(new_current, new_candidates)
    
    for node in S_minutiae.nodes():
        expand({node}, set(S_minutiae.neighbors(node)))
    
    subgraphs = [(tuple(sorted(list(s))), S_minutiae.subgraph(s).copy()) for s in risultati]
    return subgraphs

##############################
# 4) Funzione di plot finale dei due grafi con i match evidenziati
##############################

def plot_final_graphs(
    G_A, G_B, 
    matched_nodes_A, matched_nodes_B, 
    centerA, radiusA, 
    centerB, radiusB,
    output_folder, filename
):
    """
    Disegna i grafi G_A e G_B in nero, evidenziando in rosso i nodi e gli archi
    che fanno parte di almeno un match, e aggiunge una circonferenza colorata
    per mostrare l'area di ricerca in cui sono stati estratti i sotto-sottografi.
    
    - Esclude gli archi di tipo 'added'.
    - Colora i nodi a seconda del tipo (ma quelli matchati li evidenziamo in rosso).
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
    
    posA = nx.get_node_attributes(G_A, 'pos')
    posB = nx.get_node_attributes(G_B, 'pos')
    
    # Mappa colori per i tipi di nodo (usata per i NON matchati)
    color_map = {
        'ending': 'purple',
        'bifurcation': 'green',
        'core': 'blue',
        'delta': 'orange'
    }

    # 1) GRAFO A
    # Filtra archi "veri ridge"
    edges_A_no_added = [(u, v) for (u, v, data) in G_A.edges(data=True)
                        if data.get('type') != 'added']
    
    # Nodi non matchati
    non_matched_nodes_A = [n for n in G_A.nodes() if n not in matched_nodes_A]
    # Edges non matchati
    non_matched_edges_A = [(u, v) for (u, v) in edges_A_no_added
                           if (u not in matched_nodes_A) and (v not in matched_nodes_A)]
    
    # Colori per i nodi non matchati
    node_colors_A = []
    for n in non_matched_nodes_A:
        t = G_A.nodes[n].get('type', 'unknown')
        node_colors_A.append(color_map.get(t, 'black'))

    # Disegno i nodi non matchati
    nx.draw_networkx_nodes(
        G_A, posA,
        nodelist=non_matched_nodes_A,
        node_size=0.1,
        node_color=node_colors_A,
        ax=ax1
    )
    # Disegno i loro archi
    nx.draw_networkx_edges(
        G_A, posA,
        edgelist=non_matched_edges_A,
        edge_color='gray',
        width=0.1,
        ax=ax1
    )
    
    # Ora i nodi matchati (in rosso)
    matched_edges_A = [(u, v) for (u, v) in edges_A_no_added
                       if (u in matched_nodes_A) and (v in matched_nodes_A)]
    nx.draw_networkx_nodes(
        G_A, posA,
        nodelist=list(matched_nodes_A),
        node_size=0.1,
        node_color='red',
        ax=ax1
    )
    nx.draw_networkx_edges(
        G_A, posA,
        edgelist=matched_edges_A,
        edge_color='red',
        width=0.1,
        ax=ax1
    )
    
    # Disegno la circonferenza che mostra l'area di ricerca in G_A
    if centerA is not None and radiusA is not None:
        circleA = Circle(centerA, radiusA, fill=False, edgecolor='blue', linewidth=1)
        ax1.add_patch(circleA)
    
    ax1.set_title("Grafo A (match in rosso)")
    ax1.axis('off')
    ax1.set_aspect('equal', adjustable='datalim')
    
    # 2) GRAFO B
    # Filtra archi "veri ridge"
    edges_B_no_added = [(u, v) for (u, v, data) in G_B.edges(data=True)
                        if data.get('type') != 'added']
    
    non_matched_nodes_B = [n for n in G_B.nodes() if n not in matched_nodes_B]
    non_matched_edges_B = [(u, v) for (u, v) in edges_B_no_added
                           if (u not in matched_nodes_B) and (v not in matched_nodes_B)]
    
    # Colori nodi non matchati B
    node_colors_B = []
    for n in non_matched_nodes_B:
        t = G_B.nodes[n].get('type', 'unknown')
        node_colors_B.append(color_map.get(t, 'black'))

    nx.draw_networkx_nodes(
        G_B, posB,
        nodelist=non_matched_nodes_B,
        node_size=0.1,
        node_color=node_colors_B,
        ax=ax2
    )
    nx.draw_networkx_edges(
        G_B, posB,
        edgelist=non_matched_edges_B,
        edge_color='black',
        width=0.1,
        ax=ax2
    )
    
    matched_edges_B = [(u, v) for (u, v) in edges_B_no_added
                       if (u in matched_nodes_B) and (v in matched_nodes_B)]
    nx.draw_networkx_nodes(
        G_B, posB,
        nodelist=list(matched_nodes_B),
        node_size=0.1,
        node_color='red',
        ax=ax2
    )
    nx.draw_networkx_edges(
        G_B, posB,
        edgelist=matched_edges_B,
        edge_color='red',
        width=0.1,
        ax=ax2
    )
    
    # Circonferenza in G_B
    if centerB is not None and radiusB is not None:
        circleB = Circle(centerB, radiusB, fill=False, edgecolor='blue', linewidth=1)
        ax2.add_patch(circleB)
    
    ax2.set_title("Grafo B (match in rosso)")
    ax2.axis('off')
    ax2.set_aspect('equal', adjustable='datalim')
    
    plt.tight_layout()
    
    os.makedirs(output_folder, exist_ok=True)
    out_path = os.path.join(output_folder, filename)
    plt.savefig(out_path, dpi=1000)
    plt.close()
    
    print(f"Stampa finale dei grafi salvata in: {out_path}")


##############################
# 5) Funzione principale (main)
##############################

def main():
    base_folder = "/Users/riccardotortorelli/Desktop/Tesi/Archivio"
    if not os.path.exists(base_folder):
        print("Errore: La cartella specificata non esiste.")
        return

    # Carica 2 impronte
    impronte_disponibili = sorted([
        d for d in os.listdir(base_folder)
        if os.path.isdir(os.path.join(base_folder, d))
    ])
    if len(impronte_disponibili) < 2:
        print("Servono almeno 2 impronte nella cartella.")
        return

    # Scegli impronta A
    print("\nImpronte disponibili:")
    for idx, nome in enumerate(impronte_disponibili):
        print(f"{idx + 1}. {nome}")

    while True:
        try:
            sceltaA = int(input("\nSeleziona il numero dell'impronta A: ")) - 1
            if 0 <= sceltaA < len(impronte_disponibili):
                improntaA_selezionata = impronte_disponibili[sceltaA]
                break
            else:
                print("Selezione non valida per A.")
        except ValueError:
            print("Errore: inserisci un numero valido.")

    folder_A = os.path.join(base_folder, improntaA_selezionata)
    G_A, M1_A, M2_A, M3_A, M4_A = load_fingerprint_and_compute(folder_A)
    if G_A is None:
        print("Impossibile caricare impronta A.")
        return

    # Scegli impronta B
    while True:
        try:
            sceltaB = int(input("\nSeleziona il numero dell'impronta B: ")) - 1
            if 0 <= sceltaB < len(impronte_disponibili):
                improntaB_selezionata = impronte_disponibili[sceltaB]
                break
            else:
                print("Selezione non valida per B.")
        except ValueError:
            print("Errore: inserisci un numero valido.")

    folder_B = os.path.join(base_folder, improntaB_selezionata)
    G_B, M1_B, M2_B, M3_B, M4_B = load_fingerprint_and_compute(folder_B)
    if G_B is None:
        print("Impossibile caricare impronta B.")
        return

    print(f"\nImpronta A = {improntaA_selezionata}, #nodi={G_A.number_of_nodes()}, #archi={G_A.number_of_edges()}")
    print(f"Impronta B = {improntaB_selezionata}, #nodi={G_B.number_of_nodes()}, #archi={G_B.number_of_edges()}")

    # Scelta minuzia in A
    minutia_nodesA = [n for n in G_A.nodes() if G_A.nodes[n]['type'] in ('ending','bifurcation')]
    if not minutia_nodesA:
        print("Nessuna minuzia trovata in A.")
        return
    print(f"\nMinuzie disponibili in {improntaA_selezionata}:")
    for idx, node_id in enumerate(minutia_nodesA):
        node_type = G_A.nodes[node_id]['type']
        node_pos = G_A.nodes[node_id]['pos']
        print(f"{idx + 1}. Nodo {node_id} - Tipo: {node_type}, Posizione: {node_pos}")
    
    while True:
        try:
            minutia_idx = int(input(f"\nSeleziona il numero della minuzia per {improntaA_selezionata} (1-{len(minutia_nodesA)}): ")) - 1
            if 0 <= minutia_idx < len(minutia_nodesA):
                minuziaA = minutia_nodesA[minutia_idx]
                print(f"Hai selezionato il nodo {minuziaA} di tipo {G_A.nodes[minuziaA]['type']}")
                break
            else:
                print(f"Selezione non valida. Inserisci un numero tra 1 e {len(minutia_nodesA)}.")
        except ValueError:
            print("Errore: inserisci un numero valido.")
    
    # Calcolo raggio di ricerca in A (ad esempio 10% della max distanza)
    max_dist_A = max(max(row) for row in M3_A if max(row) < float('inf'))
    radiusA = 0.1 * max_dist_A
    S_A = get_subgraph_within_radius(G_A, M3_A, minuziaA, radiusA)
    print(f"Sottografo S_A con raggio={radiusA:.2f}, nodi={S_A.number_of_nodes()}, archi={S_A.number_of_edges()}")
    
    out_graphs = "/Users/riccardotortorelli/Desktop/Tesi/OutputGraph"
    os.makedirs(out_graphs, exist_ok=True)
    plot_and_save_subgraph(
        S_A, G_A, minuziaA, out_graphs,
        f"macro_subgraph_A_{improntaA_selezionata}_nodo{minuziaA}.png"
    )

    # Scelta automatica minuzia in B (quella più vicina in base a distanza euclidea dal pos di minuziaA)
    minutia_nodesB = [n for n in G_B.nodes() if G_B.nodes[n]['type'] in ('ending','bifurcation')]
    if not minutia_nodesB:
        print("Nessuna minuzia trovata in B.")
        return
    
    posA = G_A.nodes[minuziaA]['pos']
    closest_minutiaB = None
    min_distance = float('inf')
    for node_id in minutia_nodesB:
        posB = G_B.nodes[node_id]['pos']
        distance = math.dist(posA, posB)
        if distance < min_distance:
            min_distance = distance
            closest_minutiaB = node_id
    
    minuziaB = closest_minutiaB
    print(f"\nMinuzia più vicina in {improntaB_selezionata}: nodo {minuziaB} (distanza = {min_distance:.2f})")

    max_dist_B = max(max(row) for row in M3_B if max(row) < float('inf'))
    radiusB = 0.17 * max_dist_B
    S_B = get_subgraph_within_radius(G_B, M3_B, minuziaB, radiusB)
    print(f"Sottografo S_B con raggio={radiusB:.2f}, nodi={S_B.number_of_nodes()}, archi={S_B.number_of_edges()}")

    plot_and_save_subgraph(
        S_B, G_B, minuziaB, out_graphs,
        f"macro_subgraph_B_{improntaB_selezionata}_nodo{minuziaB}.png"
    )

    # -------------- MATCH SUI SOTTO-SOTTOGRAFI ---------------
    # Usiamo size=5 (puoi metterlo a 6 se vuoi)
    sub_subgraphs_A = get_connected_subgraphs_of_minutiae(S_A, size=5)
    sub_subgraphs_B = get_connected_subgraphs_of_minutiae(S_B, size=5)

    print(f"\nIn S_A abbiamo {len(sub_subgraphs_A)} sotto-sottografi (5 minuzie).")
    print(f"In S_B abbiamo {len(sub_subgraphs_B)} sotto-sottografi (5 minuzie).")

    out_subgraphs = "/Users/riccardotortorelli/Desktop/Tesi/OutputSubgraphs"
    os.makedirs(out_subgraphs, exist_ok=True)

    match_counter = 0
    matched_nodes_A = set()
    matched_nodes_B = set()

    for (subsetA, subG_A) in sub_subgraphs_A:
        for (subsetB, subG_B) in sub_subgraphs_B:
            if not subsetA or not subsetB:
                continue
            nodeA = list(subsetA)[0]
            nodeB = list(subsetB)[0]

            mapping = {}
            success = match_subgraphs(
                subG_A, subG_B,
                M1_A, M2_A, M4_A,
                M1_B, M2_B, M4_B,
                nodeA, nodeB,
                mapping=mapping,
                cost_threshold=0.1,
                max_ridge_diff=2
            )
            if success and len(mapping) == len(subG_A.nodes()):
                match_counter += 1
                print(f"\nTrovato match #{match_counter}!")
                print(f"Nodi in subG_A: {subsetA}, Nodi in subG_B: {subsetB}")
                print("Mapping:", mapping)

                matched_nodes_A.update(mapping.keys())
                matched_nodes_B.update(mapping.values())

                # Plot del singolo match
                plot_mapping(
                    subG_A, subG_B, 
                    G_A, G_B, 
                    mapping,
                    out_subgraphs,
                    f"match_{nodeA}_{nodeB}.png"
                )

    print(f"\nTotale match trovati = {match_counter}")

    # Stampa finale dei due grafi completi con i match in evidenza
    plot_final_graphs(
        G_A,
        G_B,
        matched_nodes_A,
        matched_nodes_B,
        centerA = G_A.nodes[minuziaA]['pos'],
        radiusA = radiusA,
        centerB = G_B.nodes[minuziaB]['pos'],
        radiusB = radiusB,
        output_folder = out_graphs,
        filename = "final_matches_A_B.png"
    )

    print("\n--- Elaborazione completata ---")

if __name__ == "__main__":
    main()
