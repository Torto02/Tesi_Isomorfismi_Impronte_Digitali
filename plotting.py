import os
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np


NODE_TYPE_COLOR_MAP = {
    'ending': 'red',
    'bifurcation': 'blue',
    'added': 'lightgreen',
}


FINAL_PLOT_NODE_COLOR_MAP = NODE_TYPE_COLOR_MAP

def plot_and_save_subgraph(S, G_original, source_node, output_folder, filename):
    """
    Disegna il sottografo S (estratto da G_original) e lo salva.
    - Disegna solo archi non 'added'.
    - Colora i nodi base al loro 'type' usando FINAL_PLOT_NODE_COLOR_MAP.
    - Evidenzia il nodo sorgente in giallo.
    - Aggiunge etichette (indici) ai nodi.
    - Usa stili simili a plot_final_graphs per elementi non evidenziati.
    """
    
    pos = nx.get_node_attributes(G_original, 'pos')
    
    pos_S = {node: p for node, p in pos.items() if node in S}

    if not pos_S:
        print(f"Attenzione: Nessuna posizione trovata per i nodi nel sottografo {filename}. Plot annullato.")
        return

    
    true_ridge_edges = [(u, v) for u, v, data in S.edges(data=True)
                        if data.get('type') != 'added']

    
    node_colors = []
    node_sizes = []
    node_list_S = list(S.nodes()) 
    for n in node_list_S:
        node_data = S.nodes[n]
        tipo = node_data.get('type', 'unknown')
        node_colors.append(FINAL_PLOT_NODE_COLOR_MAP.get(tipo, 'grey'))
        
        node_sizes.append(2)

    plt.figure(figsize=(9, 9))
    ax = plt.gca() 

    
    nx.draw_networkx_nodes(
        S, pos_S,
        nodelist=node_list_S,
        node_size=node_sizes,
        node_color=node_colors,
        linewidths=0, 
        
        ax=ax
    )

    
    nx.draw_networkx_edges(
        S, pos_S,
        edgelist=true_ridge_edges,
        edge_color="darkgrey", 
        width=0.2,           
        ax=ax
    )

    
    if source_node in S:
        nx.draw_networkx_nodes(
            S, pos_S,
            nodelist=[source_node],
            node_size=10,       
            node_color="yellow", 
            edgecolors='black', 
            linewidths=0.5,     
            ax=ax
        )

    
    nx.draw_networkx_labels(
        S, pos_S,
        labels={n: str(n) for n in node_list_S},
        font_size=0.5,  
        font_color="black",
        ax=ax
    )

    plt.title(f"Sottografo attorno a nodo {source_node}")
    plt.axis("off")  
    ax.set_aspect('equal', adjustable='box')  

    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, filename)
    try:
        plt.savefig(output_path, dpi=500, bbox_inches='tight')
        print(f"Immagine del sottografo salvata in: {output_path}")
    except Exception as e:
        print(f"Errore durante il salvataggio di {output_path}: {e}")
    plt.close()


def plot_mapping(S_A, S_B, G_A, G_B, mapping, output_folder, filename, score=None):
    """
    Plotta i due sottografi uno accanto all'altro con i nodi mappati colorati allo stesso modo.
    Include anche lo score del match se fornito.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 9))

    
    pos_A_orig = nx.get_node_attributes(G_A, 'pos')
    pos_B_orig = nx.get_node_attributes(G_B, 'pos')

    
    pos_A = {node: p for node, p in pos_A_orig.items() if node in S_A}
    pos_B = {node: p for node, p in pos_B_orig.items() if node in S_B}

    if not pos_A or not pos_B:
        print(f"Attenzione: Posizioni mancanti per i nodi in {filename}. Plot annullato.")
        plt.close()
        return

    # Filtra i nodi 'added'
    real_nodes_A = [n for n in S_A.nodes() if S_A.nodes[n].get('type') != 'added']
    real_nodes_B = [n for n in S_B.nodes() if S_B.nodes[n].get('type') != 'added']
    
    edges_A_no_added = [(u, v) for u, v, data in S_A.edges(data=True) if data.get('type') != 'added']
    
    node_colors_A = []
    node_sizes_A = []
    for n in real_nodes_A:
        if n in mapping.keys():
            node_type = S_A.nodes[n].get('type', 'unknown')
            
            node_colors_A.append(FINAL_PLOT_NODE_COLOR_MAP.get(node_type, 'grey'))
            node_sizes_A.append(20) 
        else:
            node_type = S_A.nodes[n].get('type', 'unknown')
            node_colors_A.append(FINAL_PLOT_NODE_COLOR_MAP.get(node_type, 'grey'))
            node_sizes_A.append(10) 

    
    edge_colors_A = []
    edge_widths_A = []
    for u, v in edges_A_no_added:
        if u in mapping.keys() and v in mapping.keys():
            edge_colors_A.append('darkgrey')
            edge_widths_A.append(0.7) 
        else:
            edge_colors_A.append('darkgrey')
            edge_widths_A.append(0.3)

    nx.draw_networkx_nodes(S_A, pos_A, nodelist=real_nodes_A, node_size=node_sizes_A,
                          node_color=node_colors_A, linewidths=0.5, edgecolors='black', ax=ax1)
    nx.draw_networkx_edges(S_A, pos_A, edgelist=edges_A_no_added,
                          edge_color=edge_colors_A, width=edge_widths_A, ax=ax1)
    
    nx.draw_networkx_labels(S_A, pos_A, labels={n: str(n) for n in real_nodes_A}, font_size=0.5, ax=ax1)

    
    edges_B_no_added = [(u, v) for u, v, data in S_B.edges(data=True) if data.get('type') != 'added']
    
    node_colors_B = []
    node_sizes_B = []
    for n in real_nodes_B:
        if n in mapping.values():
            
            node_type = S_B.nodes[n].get('type', 'unknown')
            node_colors_B.append(FINAL_PLOT_NODE_COLOR_MAP.get(node_type, 'grey'))
            node_sizes_B.append(20)
        else:
            node_type = S_B.nodes[n].get('type', 'unknown')
            node_colors_B.append(FINAL_PLOT_NODE_COLOR_MAP.get(node_type, 'grey'))
            node_sizes_B.append(10)

    
    edge_colors_B = []
    edge_widths_B = []
    for u, v in edges_B_no_added:
        if u in mapping.values() and v in mapping.values():
            edge_colors_B.append('darkgrey')
            edge_widths_B.append(0.7)
        else:
            edge_colors_B.append('darkgrey')
            edge_widths_B.append(0.3)

    nx.draw_networkx_nodes(S_B, pos_B, nodelist=real_nodes_B, node_size=node_sizes_B,
                          node_color=node_colors_B, linewidths=0.5, edgecolors='black', ax=ax2)
    nx.draw_networkx_edges(S_B, pos_B, edgelist=edges_B_no_added,
                          edge_color=edge_colors_B, width=edge_widths_B, ax=ax2)
    
    nx.draw_networkx_labels(S_B, pos_B, labels={n: str(n) for n in real_nodes_B}, font_size=0.5, ax=ax2)

    ax1.set_title(f"Sottografo A (Match: {len(mapping)} nodi)")
    ax1.axis("off")  
    ax1.set_aspect('equal', adjustable='box')

    ax2.set_title(f"Sottografo B (Match: {len(mapping)} nodi)")
    ax2.axis("off")  
    ax2.set_aspect('equal', adjustable='box')

    plt.tight_layout()
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, filename)
    
    
    
    
    
    
    if score is not None:
        plt.suptitle(f"Match Score: {score:.4f}", fontsize=16)
    
    
    plt.savefig(os.path.join(output_folder, filename), dpi=800, bbox_inches='tight')
    plt.close(fig)


def plot_final_graphs(
    G_A, G_B,
    matched_nodes_A, matched_nodes_B,
    centerA_coords, radiusA, 
    centerB_coords, radiusB, 
    output_folder, filename,
    all_matches=None  
):
    """
    Disegna i grafi completi G_A e G_B.
    - Nodi/archi non matchati: Nodi colorati per tipo (FINAL_PLOT_NODE_COLOR_MAP), archi in grigio tenue.
    - Nodi/archi matchati: Evidenziati con colori diversi per ogni sottografo matchato.
    - Disegna cerchi blu per indicare le aree di ricerca originali.
    - Esclude archi 'added' dalla visualizzazione.
    - Usa dimensioni molto piccole per nodi/archi non matchati per dare risalto ai match.
    - Aggiunge etichette (indici) SOLO ai nodi matchati.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 9))

    posA = nx.get_node_attributes(G_A, 'pos')
    posB = nx.get_node_attributes(G_B, 'pos')

    
    import matplotlib.colors as mcolors
    
    match_colors = list(mcolors.TABLEAU_COLORS.values())  
    
    match_colors.extend(['darkred', 'darkblue', 'darkgreen', 'darkorange', 'darkviolet'])
     
    node_to_color_A = {}
    node_to_color_B = {}
    
    edges_A_no_added = [(u, v) for u, v, data in G_A.edges(data=True) if data.get('type') != 'added']
    nodes_A_list = list(G_A.nodes())
    node_colors_A = []
    node_sizes_A = []
    labels_A = {}  
    for n in nodes_A_list:
            node_type = G_A.nodes[n].get('type', 'unknown')
            node_colors_A.append(FINAL_PLOT_NODE_COLOR_MAP.get(node_type, 'grey'))
            node_sizes_A.append(1)  
            labels_A[n] = str(n)

    
    nx.draw_networkx_nodes(G_A, posA, nodelist=nodes_A_list, node_size=node_sizes_A, 
                          node_color=node_colors_A, ax=ax1, linewidths=0)
    edge_colors_A = []
    edge_widths_A = []
    for u, v in edges_A_no_added:
            edge_colors_A.append('darkgrey')
            edge_widths_A.append(0.2)  


    nx.draw_networkx_edges(G_A, posA, edgelist=edges_A_no_added, edge_color=edge_colors_A, 
                          width=edge_widths_A, ax=ax1)

    nx.draw_networkx_labels(G_A, posA, labels=labels_A, font_size=0.5, font_color='black', ax=ax1)

    
    if centerA_coords and radiusA:
        circleA = Circle(centerA_coords, radiusA, fill=False, edgecolor='blue', linewidth=1, linestyle='--')
        ax1.add_patch(circleA)

    ax1.set_title(f"Grafo A ({G_A.number_of_nodes()} nodi) - Match ({len(matched_nodes_A)}) colorati")
    ax1.axis('off')  
    ax1.set_aspect('equal', adjustable='box')

    
    edges_B_no_added = [(u, v) for u, v, data in G_B.edges(data=True) if data.get('type') != 'added']
    nodes_B_list = list(G_B.nodes())

    node_colors_B = []
    node_sizes_B = []
    labels_B = {}  
    for n in nodes_B_list:
        
        
        
        
        
        
        
            node_type = G_B.nodes[n].get('type', 'unknown')
            node_colors_B.append(FINAL_PLOT_NODE_COLOR_MAP.get(node_type, 'grey'))
            node_sizes_B.append(1)
            labels_B[n] = str(n)

    nx.draw_networkx_nodes(G_B, posB, nodelist=nodes_B_list, node_size=node_sizes_B, 
                          node_color=node_colors_B, ax=ax2, linewidths=0)

    edge_colors_B = []
    edge_widths_B = []
    for u, v in edges_B_no_added:
            edge_colors_B.append('darkgrey')
            edge_widths_B.append(0.2)

    nx.draw_networkx_edges(G_B, posB, edgelist=edges_B_no_added, edge_color=edge_colors_B, 
                          width=edge_widths_B, ax=ax2)

    nx.draw_networkx_labels(G_B, posB, labels=labels_B, font_size=0.5, font_color='black', ax=ax2)

    
    if centerB_coords and radiusB:
        circleB = Circle(centerB_coords, radiusB, fill=False, edgecolor='blue', linewidth=1, linestyle='--')
        ax2.add_patch(circleB)

    ax2.set_title(f"Grafo B ({G_B.number_of_nodes()} nodi) - Match ({len(matched_nodes_B)}) colorati")
    ax2.axis('off')  
    ax2.set_aspect('equal', adjustable='box')

    plt.tight_layout()
    os.makedirs(output_folder, exist_ok=True)
    out_path = os.path.join(output_folder, filename)
    try:
        plt.savefig(out_path, dpi=800)  
        print(f"Stampa finale dei grafi salvata in: {out_path}")
    except Exception as e:
        print(f"Errore durante il salvataggio di {out_path}: {e}")
    plt.close()

def plot_match_with_context(macro_A, macro_B, sub_A, sub_B,
                            G_A, G_B, mapping,
                            out_dir, filename, score=None):
    """
    Plotta i macro-subgrafi (S_A e S_B) con evidenziato il sotto-sottografo matchato.
    I nodi 'added' non vengono visualizzati.
    """
    import matplotlib.pyplot as plt
    import os

    posA = nx.get_node_attributes(G_A, "pos")
    posB = nx.get_node_attributes(G_B, "pos")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 9))

    # --- Macro A ---
    # Filtra i nodi 'added' dal macro-grafo A
    real_nodes_macro_A = [n for n in macro_A.nodes() if macro_A.nodes[n].get("type") != "added"]
    nx.draw_networkx_nodes(macro_A, posA,
                           nodelist=real_nodes_macro_A,
                           node_size=3, node_color="lightgrey", ax=ax1)
    nx.draw_networkx_edges(macro_A, posA,
                           edgelist=[e for e in macro_A.edges()
                                     if macro_A.edges[e].get("type") != "added"],
                           width=0.2, edge_color="lightgrey", ax=ax1)
    
    # Nodi reali (non 'added') del sottografo
    real_nodes_A = [n for n in sub_A.nodes() if sub_A.nodes[n].get("type") != "added"]
    node_colors_A = [NODE_TYPE_COLOR_MAP.get(sub_A.nodes[n].get('type', 'unknown')) for n in real_nodes_A]

    nx.draw_networkx_nodes(sub_A, posA,
                           nodelist=real_nodes_A,
                           node_size=5, node_color=node_colors_A, ax=ax1,
                           edgecolors="black", linewidths=0.5)

    # Archi veri
    sub_edges_A = [e for e in sub_A.edges() if sub_A.edges[e].get("type") != "added"]
    nx.draw_networkx_edges(sub_A, posA,
                           edgelist=sub_edges_A,
                           width=0.5, edge_color="blue", ax=ax1)

    ax1.set_title("Macro Subgraph A")
    ax1.axis("off")
    ax1.set_aspect("equal")

    # --- Macro B ---
    # Filtra i nodi 'added' dal macro-grafo B
    real_nodes_macro_B = [n for n in macro_B.nodes() if macro_B.nodes[n].get("type") != "added"]
    nx.draw_networkx_nodes(macro_B, posB,
                           nodelist=real_nodes_macro_B,
                           node_size=3, node_color="lightgrey", ax=ax2)
    nx.draw_networkx_edges(macro_B, posB,
                           edgelist=[e for e in macro_B.edges()
                                     if macro_B.edges[e].get("type") != "added"],
                           width=0.2, edge_color="lightgrey", ax=ax2)

    real_nodes_B = [n for n in sub_B.nodes() if sub_B.nodes[n].get("type") != "added"]
    node_colors_B = [NODE_TYPE_COLOR_MAP.get(sub_B.nodes[n].get('type', 'unknown')) for n in real_nodes_B]

    nx.draw_networkx_nodes(sub_B, posB,
                           nodelist=real_nodes_B,
                           node_size=5, node_color=node_colors_B, ax=ax2,
                           edgecolors="black", linewidths=0.5)

    sub_edges_B = [e for e in sub_B.edges() if sub_B.edges[e].get("type") != "added"]
    nx.draw_networkx_edges(sub_B, posB,
                           edgelist=sub_edges_B,
                           width=0.5, edge_color="blue", ax=ax2)

    ax2.set_title("Macro Subgraph B")
    ax2.axis("off")
    ax2.set_aspect("equal")

    if score is not None:
        plt.suptitle(f"Match score: {score:.4f}", fontsize=14)

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, filename)
    plt.savefig(out_path, dpi=600, bbox_inches="tight")
    plt.close()

def plot_chirality_check(G_A, G_B, mapping, output_folder, filename, score=None):
    """
    Plotta i controlli di chiralità per ogni tripletta di nodi connessi nel mapping.
    Mostra i prodotti vettoriali e indica se sono coerenti o meno.
    """
    from matching import get_real_neighbors_via_added, _orientation
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
    
    # Ottieni posizioni
    pos_A = nx.get_node_attributes(G_A, 'pos')
    pos_B = nx.get_node_attributes(G_B, 'pos')
    
    # Filtra solo nodi reali nel mapping
    real_mapping = {n: mapping[n] for n in mapping.keys() 
                   if G_A.nodes[n].get('type') != 'added'}
    
    triplet_results = []
    
    # Per ogni nodo centrale nel mapping
    for nodeA, nodeB in real_mapping.items():
        neighborsA = get_real_neighbors_via_added(G_A, nodeA)
        mapped_neighbors_A = [n for n in neighborsA if n in mapping]
        
        if len(mapped_neighbors_A) < 2:
            continue
            
        # Testa tutte le combinazioni di triplette
        for i in range(len(mapped_neighbors_A)):
            for j in range(i+1, len(mapped_neighbors_A)):
                nodeA1, nodeA2 = mapped_neighbors_A[i], mapped_neighbors_A[j]
                nodeB1, nodeB2 = mapping[nodeA1], mapping[nodeA2]
                
                try:
                    # Calcola orientazioni
                    posA = pos_A[nodeA]
                    posA1 = pos_A[nodeA1] 
                    posA2 = pos_A[nodeA2]
                    cross_A = _orientation(posA, posA1, posA2)
                    
                    posB = pos_B[nodeB]
                    posB1 = pos_B[nodeB1]
                    posB2 = pos_B[nodeB2]
                    cross_B = _orientation(posB, posB1, posB2)
                    
                    # Salta se troppo piccoli (collineari)
                    if abs(cross_A) < 1e-6 or abs(cross_B) < 1e-6:
                        continue
                        
                    is_consistent = cross_A * cross_B > 0
                    
                    triplet_results.append({
                        'center_A': nodeA, 'n1_A': nodeA1, 'n2_A': nodeA2,
                        'center_B': nodeB, 'n1_B': nodeB1, 'n2_B': nodeB2,
                        'cross_A': cross_A, 'cross_B': cross_B,
                        'consistent': is_consistent
                    })
                    
                except KeyError:
                    continue
    
    # Disegna grafo A
    real_nodes_A = [n for n in G_A.nodes() if G_A.nodes[n].get('type') != 'added']
    node_colors_A = [NODE_TYPE_COLOR_MAP.get(G_A.nodes[n].get('type', 'unknown'), 'grey') 
                     for n in real_nodes_A]
    
    nx.draw_networkx_nodes(G_A, pos_A, nodelist=real_nodes_A, 
                          node_size=30, node_color=node_colors_A,
                          edgecolors='black', linewidths=0.5, ax=ax1)
    
    # Disegna archi non-added
    real_edges_A = [(u, v) for u, v, d in G_A.edges(data=True) 
                    if d.get('type') != 'added']
    nx.draw_networkx_edges(G_A, pos_A, edgelist=real_edges_A,
                          edge_color='darkgrey', width=0.5, ax=ax1)
    
    # Evidenzia nodi mappati
    mapped_nodes_A = list(real_mapping.keys())
    nx.draw_networkx_nodes(G_A, pos_A, nodelist=mapped_nodes_A,
                          node_size=50, node_color='yellow',
                          edgecolors='red', linewidths=2, ax=ax1)
    
    # Disegna grafo B
    real_nodes_B = [n for n in G_B.nodes() if G_B.nodes[n].get('type') != 'added']
    node_colors_B = [NODE_TYPE_COLOR_MAP.get(G_B.nodes[n].get('type', 'unknown'), 'grey') 
                     for n in real_nodes_B]
    
    nx.draw_networkx_nodes(G_B, pos_B, nodelist=real_nodes_B,
                          node_size=30, node_color=node_colors_B,
                          edgecolors='black', linewidths=0.5, ax=ax2)
    
    real_edges_B = [(u, v) for u, v, d in G_B.edges(data=True) 
                    if d.get('type') != 'added']
    nx.draw_networkx_edges(G_B, pos_B, edgelist=real_edges_B,
                          edge_color='darkgrey', width=0.5, ax=ax2)
    
    mapped_nodes_B = list(real_mapping.values())
    nx.draw_networkx_nodes(G_B, pos_B, nodelist=mapped_nodes_B,
                          node_size=50, node_color='yellow',
                          edgecolors='red', linewidths=2, ax=ax2)
    
    # Disegna triplette e orientamenti
    consistent_count = 0
    total_count = len(triplet_results)
    
    for idx, result in enumerate(triplet_results):
        color = 'green' if result['consistent'] else 'red'
        alpha = 0.7
        
        # Grafo A - disegna triangolo
        points_A = np.array([pos_A[result['center_A']], 
                            pos_A[result['n1_A']], 
                            pos_A[result['n2_A']]])
        triangle_A = plt.Polygon(points_A, fill=False, edgecolor=color, 
                                linewidth=2, alpha=alpha)
        ax1.add_patch(triangle_A)
        
        # Grafo B - disegna triangolo
        points_B = np.array([pos_B[result['center_B']], 
                            pos_B[result['n1_B']], 
                            pos_B[result['n2_B']]])
        triangle_B = plt.Polygon(points_B, fill=False, edgecolor=color,
                                linewidth=2, alpha=alpha)
        ax2.add_patch(triangle_B)
        
        if result['consistent']:
            consistent_count += 1
    
    # Aggiungi etichette ai nodi mappati
    nx.draw_networkx_labels(G_A, pos_A, labels={n: str(n) for n in mapped_nodes_A},
                           font_size=6, ax=ax1)
    nx.draw_networkx_labels(G_B, pos_B, labels={n: str(n) for n in mapped_nodes_B},
                           font_size=6, ax=ax2)

    consistency_rate = (consistent_count / total_count * 100) if total_count > 0 else 0
    
    ax1.set_title(f"Grafo A - Chirality Check\n{consistent_count}/{total_count} consistent ({consistency_rate:.1f}%)")
    ax1.axis('off')
    ax1.set_aspect('equal')
    
    ax2.set_title(f"Grafo B - Chirality Check\n{consistent_count}/{total_count} consistent ({consistency_rate:.1f}%)")  
    ax2.axis('off')
    ax2.set_aspect('equal')
    
    if score is not None:
        plt.suptitle(f"Chirality Analysis - Match Score: {score:.4f}", fontsize=14)
    else:
        plt.suptitle("Chirality Analysis", fontsize=14)
    
    # Legenda
    legend_elements = [
        plt.Line2D([0], [0], color='green', lw=2, label='Consistent orientation'),
        plt.Line2D([0], [0], color='red', lw=2, label='Inconsistent orientation'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='yellow', 
                  markersize=8, markeredgecolor='red', label='Mapped nodes')
    ]
    ax2.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.3, 1))
    
    plt.tight_layout()
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, filename)
    plt.savefig(output_path, dpi=600, bbox_inches='tight')
    plt.close()
    
    return consistent_count, total_count
