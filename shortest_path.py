
import os
import json
import networkx as nx
import math
import matplotlib.pyplot as plt
from collections import deque
import numpy as np

##############################
# 1) Definisci le funzioni per il matching (il tuo attuale match_subgraphs e is_cost_similar)
##############################

def is_cost_similar(cA, cB, threshold=0.2):
    """
    Ritorna True se cA e cB differiscono meno di 'threshold' (relativo).
    """
    if cA == float('inf') and cB == float('inf'):
        return True
    if cA == float('inf') or cB == float('inf'):
        return False

    denom = max(abs(cA), abs(cB), 1e-9)
    diff = abs(cA - cB) / denom
    return diff <= threshold

def match_subgraphs(
    G_A, G_B,
    M1_A, M2_A,
    M1_B, M2_B,
    nodeA, nodeB,
    mapping=None,
    visited_pairs=None,
    cost_threshold=0.2
):
    """
    DFS parallelo: cerca se il nodo 'nodeA' (in G_A) corrisponde a 'nodeB' (in G_B)
    e se i vicini matchano nei costi M1/M2.
    """
    if mapping is None:
        mapping = {}
    if visited_pairs is None:
        visited_pairs = set()

    if (nodeA, nodeB) in visited_pairs:
        return True
    visited_pairs.add((nodeA, nodeB))

    # 1) I tipi dei nodi devono coincidere
    if G_A.nodes[nodeA].get('type') != G_B.nodes[nodeB].get('type'):
        return False

    # 2) Aggiungiamo la coppia al mapping
    if nodeA in mapping and mapping[nodeA] != nodeB:
        return False
    mapping[nodeA] = nodeB

    # 3) Confronto dei vicini con un DFS parallelo
    neighborsA = list(G_A[nodeA])
    neighborsB = list(G_B[nodeB])

    for nA in neighborsA:
        found_match = False
        for nB in neighborsB:
            # già matchato altrove?
            if nB in mapping.values() and mapping.get(nA, None) != nB:
                continue

            # Confronta costi M1
            costA_m1 = M1_A[nodeA][nA]
            costB_m1 = M1_B[nodeB][nB]
            if not is_cost_similar(costA_m1, costB_m1, cost_threshold):
                continue

            # Confronta costi M2
            costA_m2 = M2_A[nodeA][nA]
            costB_m2 = M2_B[nodeB][nB]
            if not is_cost_similar(costA_m2, costB_m2, cost_threshold):
                continue

            # Ricorsione
            if match_subgraphs(G_A, G_B, M1_A, M2_A, M1_B, M2_B,
                               nA, nB, mapping, visited_pairs, cost_threshold):
                found_match = True
                break
        if not found_match:
            return False

    return True


##############################
# 2) Funzioni di supporto
##############################

def single_source_custom_dijkstra(graph, source, weight_func):
    for (u, v) in graph.edges():
        d = graph[u][v]
        d['temp_weight'] = weight_func(u, v, d)
    distances = nx.single_source_dijkstra_path_length(graph, source, weight='temp_weight')
    for (u, v) in graph.edges():
        del graph[u][v]['temp_weight']
    return distances

def get_subgraph_within_radius(G, M3, source_node, radius):
    N = G.number_of_nodes()
    sub_nodes = [j for j in range(N) if M3[source_node][j] <= radius]
    S = G.subgraph(sub_nodes).copy()
    return S

def plot_and_save_subgraph(S, G, source_node, output_folder, filename):
    pos = nx.get_node_attributes(G, 'pos')
    plt.figure(figsize=(8, 6))
    nx.draw_networkx_nodes(S, pos, node_size=50, node_color="red")
    nx.draw_networkx_edges(S, pos, edge_color="black", width=1.5)
    if source_node in S:
        nx.draw_networkx_nodes(S, pos, nodelist=[source_node],
                               node_size=100, node_color="green")
    nx.draw_networkx_labels(S, pos, labels={n: str(n) for n in S.nodes()},
                            font_size=8, font_color="black")

    plt.title(f"Sottografo attorno al nodo {source_node}")
    plt.axis("off")

    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, filename)
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Immagine del sottografo salvata in: {output_path}")

def save_matrix_to_file(matrix, filename):
    with open(filename, 'w') as f:
        for row in matrix:
            f.write(','.join(map(str, row)) + '\n')

def plot_mapping(S_A, S_B, G_A, G_B, mapping, output_folder, filename):
    """
    Visualizza il mapping tra due sottografi, mostrando le corrispondenze trovate.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Plot sottografo A
    pos_A = nx.get_node_attributes(G_A, 'pos')
    nx.draw_networkx_nodes(S_A, pos_A, node_size=50, node_color='lightblue', ax=ax1)
    nx.draw_networkx_edges(S_A, pos_A, edge_color='gray', width=1, ax=ax1)
    nx.draw_networkx_labels(S_A, pos_A, labels={n: str(n) for n in S_A.nodes()},
                          font_size=8, font_color="black", ax=ax1)
    
    # Evidenzia i nodi mappati in A
    mapped_nodes_A = list(mapping.keys())
    if mapped_nodes_A:
        nx.draw_networkx_nodes(S_A, pos_A, nodelist=mapped_nodes_A,
                             node_size=100, node_color='red', ax=ax1)
    
    ax1.set_title("Sottografo A")
    ax1.axis('off')
    
    # Plot sottografo B
    pos_B = nx.get_node_attributes(G_B, 'pos')
    nx.draw_networkx_nodes(S_B, pos_B, node_size=50, node_color='lightblue', ax=ax2)
    nx.draw_networkx_edges(S_B, pos_B, edge_color='gray', width=1, ax=ax2)
    nx.draw_networkx_labels(S_B, pos_B, labels={n: str(n) for n in S_B.nodes()},
                          font_size=8, font_color="black", ax=ax2)
    
    # Evidenzia i nodi mappati in B
    mapped_nodes_B = list(mapping.values())
    if mapped_nodes_B:
        nx.draw_networkx_nodes(S_B, pos_B, nodelist=mapped_nodes_B,
                             node_size=50, node_color='red', ax=ax2)
    
    ax2.set_title("Sottografo B")
    ax2.axis('off')
    
    plt.tight_layout()
    
    # Salva l'immagine
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, filename)
    plt.savefig(output_path, dpi=600, bbox_inches='tight')
    plt.close()
    
    print(f"Mapping visualizzato salvato in: {output_path}")

##############################
# 3) Funzione per caricare una singola impronta e calcolare M1, M2, M3
##############################

# def load_fingerprint_and_compute(folder_path):
    """
    Carica una singola impronta da folder_path, costruisce G,
    calcola M1, M2, M3 e SALVA le tre matrici in /OutputMatrices/<nomeImpronta>.
    Ritorna (G, M1, M2, M3).
    """

    nodes_file = os.path.join(folder_path, "nodes_graph.json")
    edges_file = os.path.join(folder_path, "edges_graph.json")

    if not os.path.exists(nodes_file) or not os.path.exists(edges_file):
        print(f"Errore: File nodes_graph.json o edges_graph.json non trovati in {folder_path}.")
        return None, None, None, None

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

    # Calcolo M3
    M3 = [[0.0] * N for _ in range(N)]
    coords = [G.nodes[i]['pos'] for i in range(N)]
    for i in range(N):
        for j in range(N):
            if i == j:
                M3[i][j] = 0.0
            else:
                M3[i][j] = math.dist(coords[i], coords[j])

    out_folder = "/Users/riccardotortorelli/Desktop/Tesi/OutputMatrices"
    impronta_nome = os.path.basename(folder_path)
    sub_folder = os.path.join(out_folder, impronta_nome)
    os.makedirs(sub_folder, exist_ok=True)

    save_matrix_to_file(M1, os.path.join(sub_folder, "M1.csv"))
    save_matrix_to_file(M2, os.path.join(sub_folder, "M2.csv"))
    save_matrix_to_file(M3, os.path.join(sub_folder, "M3.csv"))
    print(f"\nM1, M2, M3 salvate in: {sub_folder}")

    return G, M1, M2, M3

def load_fingerprint_and_compute(folder_path):
    """
    Carica una singola impronta da folder_path, costruisce G,
    calcola M1, M2, M3 e SALVA le tre matrici in /OutputMatrices/<nomeImpronta>.
    Ritorna (G, M1, M2, M3).
    """
    # Modifica: ora si usa nodes_simple_graph.json per avere ridge_count
    nodes_file = os.path.join(folder_path, "nodes_simple_graph.json")
    edges_file = os.path.join(folder_path, "edges_simple_graph.json")

    if not os.path.exists(nodes_file) or not os.path.exists(edges_file):
        print(f"Errore: File nodes_simple_graph.json o edges_graph.json non trovati in {folder_path}.")
        return None, None, None, None

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
        # Estrai ridge_count dal file nodes_simple_graph.json
        ridge_count = node.get('ridge_count', 0)
        G.add_node(i, pos=coord, type=ntype, ridge_count=ridge_count)

    for edge in edges:
        node1, node2 = edge['nodes']
        etype = edge.get('type', 'edge')
        dist = edge.get('distance', None)
        if node1 < len(nodes) and node2 < len(nodes):
            # Se gli archi hanno anche ridge_count, puoi gestirlo qui (altrimenti ometti)
            ridge_count_edge = edge.get('ridge_count', 0)
            G.add_edge(node1, node2, type=etype, distance=dist, ridge_count=ridge_count_edge)
        else:
            print(f"Attenzione: arco con nodi {edge['nodes']} non valido.")

    # Definizione delle funzioni di peso e calcolo di M1, M2, M3 rimangono invariate
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

    # Calcolo M3: matrice delle distanze euclidee dirette
    M3 = [[0.0] * N for _ in range(N)]
    coords = [G.nodes[i]['pos'] for i in range(N)]
    for i in range(N):
        for j in range(N):
            if i == j:
                M3[i][j] = 0.0
            else:
                M3[i][j] = math.dist(coords[i], coords[j])

    out_folder = "/Users/riccardotortorelli/Desktop/Tesi/OutputMatrices"
    impronta_nome = os.path.basename(folder_path)
    sub_folder = os.path.join(out_folder, impronta_nome)
    os.makedirs(sub_folder, exist_ok=True)

    save_matrix_to_file(M1, os.path.join(sub_folder, "M1.csv"))
    save_matrix_to_file(M2, os.path.join(sub_folder, "M2.csv"))
    save_matrix_to_file(M3, os.path.join(sub_folder, "M3.csv"))
    print(f"\nM1, M2, M3 salvate in: {sub_folder}")

    return G, M1, M2, M3

##############################
# Aggiunta di una funzione di correzione distorsione (opzionale)
##############################

def apply_distortion_correction(M2, distortion_factor=1.0):
    """
    Applies a correction factor to compensate for global distortions in M2 matrix.
    """
    N = len(M2)
    corrected_M2 = [[0.0] * N for _ in range(N)]
    
    for i in range(N):
        for j in range(N):
            if M2[i][j] == float('inf'):
                corrected_M2[i][j] = float('inf')
            else:
                corrected_M2[i][j] = M2[i][j] * distortion_factor
            
    return corrected_M2

##############################
# 4) NUOVA CLASSE "FingerprintMatcher" con un matching più fine su micro-sottografi
##############################

class FingerprintMatcher:
    """
    Classe che gestisce il matching di piccoli sottografi (4-6 minuzie)
    con tolleranze su distanze, 'salti' di ridge, ecc.
    """
    def __init__(self):
        self.matches = []
        self.similarity_scores = []
    
    def extract_subgraph_bfs(self, graph, center_node, max_nodes=6, max_distance_ratio=1/3):     
        """
        Estrae un sottografo (con BFS) centrato su center_node,
        limitato a un massimo di max_nodes e a un raggio euclideo = max_distance_ratio * dimensione impronta
        """
        pos_attr = nx.get_node_attributes(graph, 'pos')
        all_positions = np.array(list(pos_attr.values()))
        if len(all_positions) == 0:
            return graph.subgraph([center_node]).copy()

        # dimensione impronta = max differenza su bounding box
        min_xy = np.min(all_positions, axis=0)
        max_xy = np.max(all_positions, axis=0)
        fingerprint_size = np.max(max_xy - min_xy)
        max_distance = fingerprint_size * max_distance_ratio

        sub_nodes = [center_node]
        queue = deque([center_node])
        visited = set([center_node])

        while queue and len(sub_nodes) < max_nodes:
            node = queue.popleft()
            for neighbor in graph.neighbors(node):
                if neighbor not in visited:
                    # distanza euclidea
                    dist_eucl = math.dist(pos_attr[node], pos_attr[neighbor])
                    if dist_eucl <= max_distance:
                        visited.add(neighbor)
                        sub_nodes.append(neighbor)
                        queue.append(neighbor)
                        if len(sub_nodes) >= max_nodes:
                            break
        
        return graph.subgraph(sub_nodes).copy()

    def are_similar_nodes(self, node1, node2, g1, g2, tolerance=2):
        """
        Confronta due nodi (tipo di minuzia, eventuale ridge_count) con tolleranza.
        """
        if g1.nodes[node1].get('type') != g2.nodes[node2].get('type'):
            return False
        
        # se hai attributi come "ridge_count" puoi confrontarli
        rc1 = g1.nodes[node1].get('ridge_count', 0)
        rc2 = g2.nodes[node2].get('ridge_count', 0)
        if abs(rc1 - rc2) > tolerance:
            return False
        
        return True
    
    def compare_edge_properties(self, edge1, edge2, g1, g2, tolerance=2):
        """
        Confronta le proprietà di due archi.
        """
        # se hai attributi come "length"
        length1 = g1.edges[edge1].get('distance')
        length2 = g2.edges[edge2].get('distance')

        if length1 is not None and length2 is not None:
            diff = abs(length1 - length2)
            avg_len = (length1 + length2) / 2 if (length1 + length2) != 0 else 1
            if diff / avg_len > 0.3:  # 30% di tolleranza
                return False
        
        # se hai "ridge_count" sugli archi
        rc1 = g1.edges[edge1].get('ridge_count', 0)
        rc2 = g2.edges[edge2].get('ridge_count', 0)
        if abs(rc1 - rc2) > tolerance:
            return False

        return True
    
    def _dfs_match(self, g1, g2, node1, node2, mapping, visited1, tolerance):
        """
        DFS ricorsiva di supporto, simile a match_subgraphs,
        ma localizzata al sottografo e con compare_edge_properties personalizzato.
        """
        for nbr1 in g1.neighbors(node1):
            if nbr1 in visited1:
                continue
            
            found_match = False
            for nbr2 in g2.neighbors(node2):
                if nbr2 in mapping.values():
                    continue
                
                # check se i nodi corrispondono
                if self.are_similar_nodes(nbr1, nbr2, g1, g2, tolerance):
                    # check archi
                    if self.compare_edge_properties((node1,nbr1), (node2,nbr2), g1, g2, tolerance):
                        visited1.add(nbr1)
                        mapping[nbr1] = nbr2

                        success, newmap = self._dfs_match(g1,g2,nbr1,nbr2,mapping,visited1,tolerance)
                        if success:
                            found_match = True
                            mapping = newmap
                            break
                        
                        # backtrack
                        del mapping[nbr1]
                        visited1.remove(nbr1)
            
            if not found_match:
                # se non abbiamo match per questo vicino, 
                # potremmo terminare se il mapping ha almeno 4 nodi
                if len(mapping) >= 4:
                    return True, mapping
                else:
                    return False, mapping
        
        # se abbiamo coperto tutti i vicini e mappato >=4 nodi
        return (len(mapping) >= 4), mapping

    def subgraph_isomorphism_dfs(self, sg1, sg2, tolerance=2):
        """
        Tenta di trovare un mapping (>=4 nodi) tra sg1 e sg2,
        restituendo (mapping, score).
        """
        if len(sg1) < 4 or len(sg2) < 4:
            return None, 0

        best_mapping = None
        best_score = 0
        
        # Prova tutti i nodi come start node
        for n1 in sg1.nodes():
            for n2 in sg2.nodes():
                if self.are_similar_nodes(n1,n2,sg1,sg2,tolerance):
                    mapping = {n1: n2}
                    visited1 = set([n1])
                    success, outmap = self._dfs_match(sg1, sg2, n1, n2, mapping, visited1, tolerance)
                    if success:
                        score = self._calc_score(sg1, sg2, outmap, tolerance)
                        if score > best_score:
                            best_score = score
                            best_mapping = dict(outmap)
        
        return best_mapping, best_score

    def _calc_score(self, sg1, sg2, mapping, tolerance):
        """
        Calcola un punteggio di similarità 0-1
        """
        mapped_nodes = len(mapping)
        # contiamo archi
        possible_edges = 0
        mapped_edges = 0

        for u1,v1 in sg1.edges():
            if (u1 in mapping) and (v1 in mapping):
                possible_edges += 1
                u2, v2 = mapping[u1], mapping[v1]
                if sg2.has_edge(u2,v2) and self.compare_edge_properties((u1,v1),(u2,v2),sg1,sg2,tolerance):
                    mapped_edges += 1
        
        # normalizzazione
        node_score = mapped_nodes / max(1, min(len(sg1), len(sg2)))
        if possible_edges == 0:
            edge_score = 0
        else:
            edge_score = mapped_edges / possible_edges
        
        final_score = 0.4*node_score + 0.6*edge_score
        return final_score

    def find_matches(self, graph1, graph2, min_nodes=4, max_nodes=6,
                     max_distance_ratio=1/3, tolerance=2, min_score=0.7):
        """
        Trova match fra micro-sottografi di graph1 e graph2.
        """
        self.matches = []
        self.similarity_scores = []

        # Scorri tutte le minuzie
        for m1 in graph1.nodes():
            # Filtra se non è 'added' o 'border', se vuoi
            if graph1.nodes[m1].get('type') in ('added','border'):
                continue

            for m2 in graph2.nodes():
                if graph2.nodes[m2].get('type') in ('added','border'):
                    continue

                # Verifica tipo base
                if self.are_similar_nodes(m1, m2, graph1, graph2, tolerance):
                    # estrai subgrafo BFS
                    sg1 = self.extract_subgraph_bfs(graph1, m1, max_nodes, max_distance_ratio)
                    sg2 = self.extract_subgraph_bfs(graph2, m2, max_nodes, max_distance_ratio)
                    mapping, score = self.subgraph_isomorphism_dfs(sg1, sg2, tolerance)
                    if mapping and score >= min_score and len(mapping) >= min_nodes:
                        self.matches.append((sg1, sg2, mapping, score))
                        self.similarity_scores.append(score)
        
        return self.matches

    def visualize_match(self, match_idx=0, figsize=(12,6)):
        if not self.matches or match_idx>=len(self.matches):
            print("Nessun match da visualizzare")
            return
        sg1, sg2, mapping, score = self.matches[match_idx]

        fig, (ax1, ax2) = plt.subplots(1,2, figsize=figsize)
        pos1 = nx.get_node_attributes(sg1,'pos')
        pos2 = nx.get_node_attributes(sg2,'pos')

        nx.draw(sg1, pos1, ax=ax1, with_labels=True, node_color='lightblue')
        nx.draw(sg2, pos2, ax=ax2, with_labels=True, node_color='lightgreen')

        # evidenzia nodi mappati
        mapped_n1 = list(mapping.keys())
        mapped_n2 = list(mapping.values())
        nx.draw_networkx_nodes(sg1, pos1, nodelist=mapped_n1, node_color='red', ax=ax1)
        nx.draw_networkx_nodes(sg2, pos2, nodelist=mapped_n2, node_color='red', ax=ax2)

        ax1.set_title("Sottografo 1")
        ax2.set_title("Sottografo 2")
        fig.suptitle(f"Match con score={score:.2f}", fontsize=14)
        plt.tight_layout()
        plt.show()

    def summarize_matches(self):
        if not self.matches:
            return {"num_matches":0}
        arr = np.array(self.similarity_scores)
        return {
            "num_matches": len(self.matches),
            "avg_score": arr.mean(),
            "max_score": arr.max(),
            "min_score": arr.min(),
            "avg_nodes_mapped": np.mean([len(m[2]) for m in self.matches])
        }

##############################
# 5) Funzione principale che carica e confronta due impronte
##############################

def main():
    base_folder = "/Users/riccardotortorelli/Desktop/Tesi/Archivio"
    if not os.path.exists(base_folder):
        print("Errore: La cartella specificata non esiste.")
        return

    # Elenco delle impronte disponibili
    impronte_disponibili = sorted([d for d in os.listdir(base_folder)
                                   if os.path.isdir(os.path.join(base_folder, d))])
    if len(impronte_disponibili) < 2:
        print("Servono almeno 2 impronte nella cartella.")
        return

    # 1) SCELTA IMPRONTA A
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
                print("Selezione non valida, inserisci un numero corretto per A.")
        except ValueError:
            print("Errore: inserisci un numero valido.")

    folder_A = os.path.join(base_folder, improntaA_selezionata)
    G_A, M1_A, M2_A, M3_A = load_fingerprint_and_compute(folder_A)
    if G_A is None:
        print("Impossibile caricare impronta A.")
        return

    # 2) SCELTA IMPRONTA B
    while True:
        try:
            sceltaB = int(input("\nSeleziona il numero dell'impronta B: ")) - 1
            if 0 <= sceltaB < len(impronte_disponibili) and sceltaB != sceltaA:
                improntaB_selezionata = impronte_disponibili[sceltaB]
                break
            else:
                print("Selezione non valida, inserisci un numero corretto per B (diverso da A).")
        except ValueError:
            print("Errore: inserisci un numero valido.")

    folder_B = os.path.join(base_folder, improntaB_selezionata)
    G_B, M1_B, M2_B, M3_B = load_fingerprint_and_compute(folder_B)
    if G_B is None:
        print("Impossibile caricare impronta B.")
        return

    print(f"\nImpronta A = {improntaA_selezionata}, nodi={G_A.number_of_nodes()}, archi={G_A.number_of_edges()}")
    print(f"Impronta B = {improntaB_selezionata}, nodi={G_B.number_of_nodes()}, archi={G_B.number_of_edges()}")
    
    # Nuova funzione per plottare i grafi
    def plot_and_save_graphs(graph, impronta_nome, output_folder, color='blue'):
        """
        Visualizza e salva un grafo con uno stile simile a quello usato in dfs_graph.py
        """
        os.makedirs(output_folder, exist_ok=True)
        
        plt.figure(figsize=(15, 12))
        pos = nx.get_node_attributes(graph, 'pos')
        
        # Disegna i nodi
        nx.draw_networkx_nodes(graph, pos, node_size=5, node_color=color)
        
        # Disegna gli archi
        nx.draw_networkx_edges(graph, pos, edge_color='black', width=0.3)
        
        # Aggiungi le etichette dei nodi
        nx.draw_networkx_labels(graph, pos, labels={n: str(n) for n in graph.nodes()},
                              font_size=2, font_color="black")
        
        # Evidenzia i nodi speciali (minuzie)
        minutiae = [n for n in graph.nodes() if graph.nodes[n].get('type') in ('ending', 'bifurcation')]
        if minutiae:
            nx.draw_networkx_nodes(graph, pos, nodelist=minutiae, 
                                 node_color='red', node_size=5)
        
        plt.title(f"Grafo dell'Impronta: {impronta_nome}")
        plt.axis('off')
        
        # Salva l'immagine
        output_path = os.path.join(output_folder, f"graph_{impronta_nome}.png")
        plt.savefig(output_path, dpi=600, bbox_inches='tight')
        plt.close()
        
        print(f"Immagine del grafo salvata in: {output_path}")
    
    # Usa la nuova funzione per plottare i grafi
    graph_plot_folder = "/Users/riccardotortorelli/Desktop/Tesi/OutputGraphs"
    plot_and_save_graphs(G_A, improntaA_selezionata, graph_plot_folder, color='blue')
    plot_and_save_graphs(G_B, improntaB_selezionata, graph_plot_folder, color='blue')
    
    # 3) Estrazione sottografo A
    # minutieA = [n for n in G_A.nodes() if G_A.nodes[n].get('type') in ('ending','bifurcation')]
    # if not minutieA:
    #     print("Nessuna minuzia trovata in impronta A.")
    #     return
    # minuziaA = minutieA[0]
    minutieA = [n for n in G_A.nodes() if G_A.nodes[n].get('type') in ('ending','bifurcation')]
    if not minutieA:
        print("Nessuna minuzia trovata in impronta A.")
        return

    print("\nMinuzie disponibili nell'impronta A:")
    for idx, n in enumerate(minutieA):
        tipo = G_A.nodes[n].get('type')
        pos = G_A.nodes[n].get('pos')
        print(f"{idx}: nodo {n}, tipo: {tipo}, posizione: {pos}")

    while True:
        try:
            scelta_idx_A = int(input("\nInserisci l'indice della minuzia per il sottografo A: "))
            if 0 <= scelta_idx_A < len(minutieA):
                minuziaA = minutieA[scelta_idx_A]
                break
            else:
                print(f"Inserisci un numero tra 0 e {len(minutieA)-1}.")
        except ValueError:
            print("Inserisci un numero valido.")

    max_dist_A = max(max(row) for row in M3_A if max(row) < float('inf'))
    radiusA = 0.1 * max_dist_A
    S_A = get_subgraph_within_radius(G_A, M3_A, minuziaA, radiusA)

    # 4) Estrazione sottografo B
    # minutieB = [n for n in G_B.nodes() if G_B.nodes[n].get('type') in ('ending','bifurcation')]
    # if not minutieB:
    #     print("Nessuna minuzia trovata in impronta B.")
    #     return
    # minuziaB = minutieB[0]
    minutieB = [n for n in G_B.nodes() if G_B.nodes[n].get('type') in ('ending','bifurcation')]
    if not minutieB:
        print("Nessuna minuzia trovata in impronta B.")
        return

    print("\nMinuzie disponibili nell'impronta B:")
    for idx, n in enumerate(minutieB):
        tipo = G_B.nodes[n].get('type')
        pos = G_B.nodes[n].get('pos')
        print(f"{idx}: nodo {n}, tipo: {tipo}, posizione: {pos}")

    while True:
        try:
            scelta_idx_B = int(input("\nInserisci l'indice della minuzia per il sottografo B: "))
            if 0 <= scelta_idx_B < len(minutieB):
                minuziaB = minutieB[scelta_idx_B]
                break
            else:
                print(f"Inserisci un numero tra 0 e {len(minutieB)-1}.")
        except ValueError:
            print("Inserisci un numero valido.")

    max_dist_B = max(max(row) for row in M3_B if max(row) < float('inf'))
    radiusB = 0.1 * max_dist_B
    S_B = get_subgraph_within_radius(G_B, M3_B, minuziaB, radiusB)

    print(f"\nSottografo A con raggio={radiusA:.2f}, nodi={S_A.number_of_nodes()}, archi={S_A.number_of_edges()}")
    print(f"Sottografo B con raggio={radiusB:.2f}, nodi={S_B.number_of_nodes()}, archi={S_B.number_of_edges()}")

    # Salvataggio subgrafi
    out_subgraphs = "/Users/riccardotortorelli/Desktop/Tesi/OutputSubgraphs"
    plot_and_save_subgraph(S_A, G_A, minuziaA, out_subgraphs, f"subgraphA_{minuziaA}.png")
    plot_and_save_subgraph(S_B, G_B, minuziaB, out_subgraphs, f"subgraphB_{minuziaB}.png")

    # Esempio: Distortion correction su M2_B
    distortion_factors = [1.0, 1.5, 2.0]  # Prova con 1.0 (senza distorsione)
    
    # USO DEL NUOVO "FingerprintMatcher"
    matcher = FingerprintMatcher()
    best_global_score = 0
    best_mapping_info = None

    for df in distortion_factors:
        M2_B_corrected = apply_distortion_correction(M2_B, df)
        print(f"\nRicerca micro-match con distortion_factor={df} ...")

        # Esempio: matcha i due grafi
        # matches = matcher.find_matches(
        #     G_A, G_B,
        #     min_nodes=4,  # richiedi almeno 4 nodi
        #     max_nodes=6,  # micro-sottografi di 6 nodi max
        #     max_distance_ratio=0.33,  # 1/3 dimensione
        #     tolerance=2,
        #     min_score=0.5
        # )
        matches = matcher.find_matches(
            S_A, S_B,  # Usa i sottografi precedentemente estratti
            min_nodes=4,
            max_nodes=6,
            max_distance_ratio=0.33,
            tolerance=2,
            min_score=0.5
        )
        print(f"Trovati {len(matches)} match con distortion_factor={df}")
        if matches:
            # prendi il migliore
            best_idx = np.argmax([m[3] for m in matches])  # m[3]=score
            sg1, sg2, mapping, score = matches[best_idx]
            if score > best_global_score:
                best_global_score = score
                best_mapping_info = (df, best_idx, sg1, sg2, mapping, score)

    if best_mapping_info is not None:
        df, best_idx, sg1, sg2, mapping, score = best_mapping_info
        print(f"\nMiglior match con distortion={df}, score={score:.2f}, nodi mappati={len(mapping)}")

        # Visualizza 
        matcher.matches = [(sg1, sg2, mapping, score)]  # forza un solo match
        matcher.visualize_match(0)
    else:
        print("Nessun micro-match trovato con i parametri correnti.")

    print("\n--- Elaborazione completata ---")


if __name__ == "__main__":
    main()
