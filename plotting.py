import os
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

# Mappa colori standard per i tipi di nodo (usata da più funzioni)
NODE_TYPE_COLOR_MAP = {
    'ending': 'red',
    'bifurcation': 'blue',
    'core': 'cyan',
    'delta': 'gold',
    'added': 'none',  # verrà comunque filtrato, ma se volessi colorarli "trasparenti"
    'unknown': 'grey' # Colore per tipi non specificati
}

# Mappa colori per plot finale (ora identica alla mappa standard per coerenza)
FINAL_PLOT_NODE_COLOR_MAP = NODE_TYPE_COLOR_MAP

# Mappa colori per i tipi di archi
EDGE_TYPE_COLOR_MAP = {
    'ridge': 'darkblue',
    'added': 'none',  # verrà filtrato
    'unknown': 'grey'  # Colore per tipi non specificati
}

# Mappa colori per archi nel plot finale
FINAL_PLOT_EDGE_COLOR_MAP = EDGE_TYPE_COLOR_MAP


def plot_and_save_subgraph(S, G_original, source_node, output_folder, filename):
    """
    Disegna il sottografo S (estratto da G_original) e lo salva.
    - Esclude nodi e archi di tipo 'added'.
    - Colora i nodi base al loro 'type' usando NODE_TYPE_COLOR_MAP.
    - Colora gli archi base al loro 'type' usando EDGE_TYPE_COLOR_MAP.
    - Evidenzia il nodo sorgente in rosso.
    - Aggiunge etichette (indici) ai nodi.
    """
    # Ottieni posizioni dal grafo originale G_original per coerenza
    pos_original = nx.get_node_attributes(G_original, 'pos')
    # Copia solo le posizioni relative ai nodi presenti in S
    pos_S = {n: pos_original[n] for n in S.nodes if n in pos_original}

    if not pos_S:
        print(f"Attenzione: Nessuna posizione trovata per i nodi nel sottografo {filename}. Plot annullato.")
        return

    # ---- Filtro nodi e archi 'added' ----
    # Nodi da disegnare (escludo quelli di tipo 'added')
    nodes_to_draw = [n for n in S.nodes if S.nodes[n].get('type') != 'added']
    # Aggiorno posizioni in base al filtro nodi
    pos_S = {n: pos_S[n] for n in nodes_to_draw if n in pos_S}
    # Archi "veri" (escludo quelli 'added' e controllo che i nodi siano nel set filtrato)
    edges_to_draw = [(u, v) for u, v, data in S.edges(data=True)
                     if data.get('type') != 'added' and u in nodes_to_draw and v in nodes_to_draw]

    # Costruisco la lista di colori corrispondente ai nodi
    node_colors = []
    node_sizes = []
    for n in nodes_to_draw:
        tipo = S.nodes[n].get('type', 'unknown')
        node_colors.append(FINAL_PLOT_NODE_COLOR_MAP.get(tipo, 'grey'))
        node_sizes.append(15)  # dimensione standard

    # Costruisco la lista di colori per gli archi
    edge_colors = []
    for (u, v) in edges_to_draw:
        edge_data = S.get_edge_data(u, v)
        edge_type = edge_data.get('type', 'unknown')
        edge_colors.append(EDGE_TYPE_COLOR_MAP.get(edge_type, 'grey'))

    plt.figure(figsize=(18, 9))
    ax = plt.gca()  # Get current axes

    # Disegno i nodi filtrati
    nx.draw_networkx_nodes(
        S, pos_S,
        nodelist=nodes_to_draw,
        node_size=node_sizes,
        node_color=node_colors,
        linewidths=0.5,  # bordo sottile
        edgecolors='black',
        ax=ax
    )

    # Disegno gli archi filtrati
    nx.draw_networkx_edges(
        S, pos_S,
        edgelist=edges_to_draw,
        edge_color=edge_colors,
        width=0.5,
        ax=ax
    )

    # Evidenzio il nodo sorgente (se ancora presente dopo il filtro)
    if source_node in nodes_to_draw:
        nx.draw_networkx_nodes(
            S, pos_S,
            nodelist=[source_node],
            node_size=15,
            node_color="red",   # colore più visibile
            edgecolors='black', # bordo
            linewidths=1.0,
            ax=ax
        )

    # Label sui nodi (Indice del nodo)
    nx.draw_networkx_labels(
        S, pos_S,
        labels={n: str(n) for n in nodes_to_draw},
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


def plot_mapping(S_A, S_B, G_A, G_B, mapping, output_folder, filename):
    """
    Visualizza il mapping tra due sottografi S_A e S_B.
    - Esclude nodi e archi di tipo 'added'.
    - Colora nodi base al tipo (FINAL_PLOT_NODE_COLOR_MAP).
    - Colora archi base al tipo (EDGE_TYPE_COLOR_MAP).
    - Evidenzia i nodi mappati (chiavi e valori di 'mapping') in rosso.
    - Aggiunge etichette (indici) ai nodi.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 9))

    # Ottieni posizioni dai grafi originali
    pos_A_orig = nx.get_node_attributes(G_A, 'pos')
    pos_B_orig = nx.get_node_attributes(G_B, 'pos')

    # ----- Filtraggio S_A -----
    nodes_A_no_added = [n for n in S_A.nodes if S_A.nodes[n].get('type') != 'added']
    pos_A = {n: pos_A_orig[n] for n in nodes_A_no_added if n in pos_A_orig}
    edges_A_no_added = [(u, v) for u, v, data in S_A.edges(data=True)
                        if data.get('type') != 'added' and u in nodes_A_no_added and v in nodes_A_no_added]

    # ----- Filtraggio S_B -----
    nodes_B_no_added = [n for n in S_B.nodes if S_B.nodes[n].get('type') != 'added']
    pos_B = {n: pos_B_orig[n] for n in nodes_B_no_added if n in pos_B_orig}
    edges_B_no_added = [(u, v) for u, v, data in S_B.edges(data=True)
                        if data.get('type') != 'added' and u in nodes_B_no_added and v in nodes_B_no_added]

    if not pos_A or not pos_B:
        print(f"Attenzione: Posizioni mancanti per i nodi in {filename}. Plot annullato.")
        plt.close()
        return

    # --- Plot Sottografo A ---
    node_colors_A = []
    node_sizes_A = []
    for n in nodes_A_no_added:
        if n in mapping.keys():
            node_colors_A.append('red')
            node_sizes_A.append(20)  # più grande se mappato
        else:
            node_type = S_A.nodes[n].get('type', 'unknown')
            node_colors_A.append(FINAL_PLOT_NODE_COLOR_MAP.get(node_type, 'grey'))
            node_sizes_A.append(10)

    edge_colors_A = []
    edge_widths_A = []
    for u, v in edges_A_no_added:
        if u in mapping.keys() and v in mapping.keys():
            edge_colors_A.append('red')
            edge_widths_A.append(0.7)
        else:
            edge_type = S_A.get_edge_data(u, v).get('type', 'unknown')
            edge_colors_A.append(EDGE_TYPE_COLOR_MAP.get(edge_type, 'darkgrey'))
            edge_widths_A.append(0.3)

    nx.draw_networkx_nodes(S_A, pos_A, nodelist=nodes_A_no_added, node_size=node_sizes_A,
                           node_color=node_colors_A, linewidths=0.5, edgecolors='black', ax=ax1)
    nx.draw_networkx_edges(S_A, pos_A, edgelist=edges_A_no_added,
                           edge_color=edge_colors_A, width=edge_widths_A, ax=ax1)
    # Label nodi
    nx.draw_networkx_labels(S_A, pos_A,
                            labels={n: str(n) for n in nodes_A_no_added},
                            font_size=0.5, ax=ax1)

    # --- Plot Sottografo B ---
    node_colors_B = []
    node_sizes_B = []
    for n in nodes_B_no_added:
        if n in mapping.values():
            node_colors_B.append('red')
            node_sizes_B.append(20)
        else:
            node_type = S_B.nodes[n].get('type', 'unknown')
            node_colors_B.append(FINAL_PLOT_NODE_COLOR_MAP.get(node_type, 'grey'))
            node_sizes_B.append(10)

    edge_colors_B = []
    edge_widths_B = []
    for u, v in edges_B_no_added:
        if u in mapping.values() and v in mapping.values():
            edge_colors_B.append('red')
            edge_widths_B.append(0.7)
        else:
            edge_colors_B.append('darkgrey')
            edge_widths_B.append(0.3)

    nx.draw_networkx_nodes(S_B, pos_B, nodelist=nodes_B_no_added, node_size=node_sizes_B,
                           node_color=node_colors_B, linewidths=0.5, edgecolors='black', ax=ax2)
    nx.draw_networkx_edges(S_B, pos_B, edgelist=edges_B_no_added,
                           edge_color=edge_colors_B, width=edge_widths_B, ax=ax2)
    # Label nodi
    nx.draw_networkx_labels(S_B, pos_B,
                            labels={n: str(n) for n in nodes_B_no_added},
                            font_size=0.5, ax=ax2)

    ax1.set_title(f"Sottografo A (Match: {len(mapping)} nodi)")
    ax1.axis("off")
    ax1.set_aspect('equal', adjustable='box')

    ax2.set_title(f"Sottografo B (Match: {len(mapping)} nodi)")
    ax2.axis("off")
    ax2.set_aspect('equal', adjustable='box')

    plt.tight_layout()
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, filename)
    try:
        plt.savefig(output_path, dpi=500, bbox_inches='tight')
        print(f"Mapping visualizzato salvato in: {output_path}")
    except Exception as e:
        print(f"Errore durante il salvataggio di {output_path}: {e}")
    plt.close()


def plot_final_graphs(
    G_A, G_B,
    matched_nodes_A, matched_nodes_B,
    centerA_coords, radiusA,  # Posizione e raggio per il cerchio A
    centerB_coords, radiusB,  # Posizione e raggio per il cerchio B
    output_folder, filename,
    all_matches=None  # lista di dizionari con i match {'map': mapping, 'nodes_A': set(), 'nodes_B': set()}
):
    """
    Disegna i grafi completi G_A e G_B escludendo nodi/archi 'added'.
    - Nodi/archi non matchati: colorati in base al loro 'type'.
    - Nodi/archi matchati: evidenziati con colori diversi (uno per match).
    - Disegna cerchi blu per indicare le aree di ricerca originali.
    - Usa dimensioni piccole per i nodi/archi non matchati e più grandi per i matchati.
    - Etichette (indici) SOLO sui nodi matchati.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 9))

    posA = nx.get_node_attributes(G_A, 'pos')
    posB = nx.get_node_attributes(G_B, 'pos')

    # ----- Filtri per G_A -----
    nodes_A_no_added = [n for n in G_A.nodes if G_A.nodes[n].get('type') != 'added']
    edges_A_no_added = [(u, v) for u, v, d in G_A.edges(data=True)
                        if d.get('type') != 'added' and u in nodes_A_no_added and v in nodes_A_no_added]

    # ----- Filtri per G_B -----
    nodes_B_no_added = [n for n in G_B.nodes if G_B.nodes[n].get('type') != 'added']
    edges_B_no_added = [(u, v) for u, v, d in G_B.edges(data=True)
                        if d.get('type') != 'added' and u in nodes_B_no_added and v in nodes_B_no_added]

    # Genera una lista di colori distinti per i diversi match
    import matplotlib.colors as mcolors
    match_colors = list(mcolors.TABLEAU_COLORS.values())  # 10 colori
    # Aggiungi altri colori se necessario
    match_colors.extend(['darkred', 'darkblue', 'darkgreen', 'darkorange', 'darkviolet'])

    # Crea dizionari per mappare nodi ai colori dei loro match
    node_to_color_A = {}
    node_to_color_B = {}

    # Se abbiamo la lista dei match, assegna colori diversi a ciascun match
    if all_matches:
        for i, match_info in enumerate(all_matches):
            color_idx = i % len(match_colors)
            color = match_colors[color_idx]
            for node_a in match_info['nodes_A']:
                node_to_color_A[node_a] = color
            for node_b in match_info['nodes_B']:
                node_to_color_B[node_b] = color

    # --- GRAFO A ---
    node_colors_A = []
    node_sizes_A = []
    labels_A = {}
    for n in nodes_A_no_added:
        if n in matched_nodes_A:
            # Se è in all_matches, prendo il colore dedicato, altrimenti 'red'
            color_match = node_to_color_A.get(n, 'red')
            node_colors_A.append(color_match)
            node_sizes_A.append(5)
            labels_A[n] = str(n)  # etichetta solo se matchato
        else:
            node_type = G_A.nodes[n].get('type', 'unknown')
            node_colors_A.append(FINAL_PLOT_NODE_COLOR_MAP.get(node_type, 'grey'))
            node_sizes_A.append(1)

    nx.draw_networkx_nodes(G_A, posA, nodelist=nodes_A_no_added,
                           node_size=node_sizes_A, node_color=node_colors_A,
                           ax=ax1, linewidths=0)

    edge_colors_A = []
    edge_widths_A = []
    for (u, v) in edges_A_no_added:
        if u in matched_nodes_A and v in matched_nodes_A:
            # Se entrambi matchati e stesso colore di match, uso quello
            if (u in node_to_color_A and v in node_to_color_A and 
                node_to_color_A[u] == node_to_color_A[v]):
                edge_colors_A.append(node_to_color_A[u])
            else:
                edge_colors_A.append('red')
            edge_widths_A.append(0.5)
        else:
            edge_type = G_A.get_edge_data(u, v).get('type', 'unknown')
            edge_colors_A.append(FINAL_PLOT_EDGE_COLOR_MAP.get(edge_type, 'darkgrey'))
            edge_widths_A.append(0.1)

    nx.draw_networkx_edges(G_A, posA, edgelist=edges_A_no_added,
                           edge_color=edge_colors_A, width=edge_widths_A, ax=ax1)
    nx.draw_networkx_labels(G_A, posA, labels=labels_A, font_size=0.5, font_color='black', ax=ax1)

    # Disegno la circonferenza A
    if centerA_coords and radiusA:
        circleA = Circle(centerA_coords, radiusA, fill=False, edgecolor='blue', linewidth=1, linestyle='--')
        ax1.add_patch(circleA)

    ax1.set_title(f"Grafo A ({G_A.number_of_nodes()} nodi) - Match ({len(matched_nodes_A)}) colorati")
    ax1.axis('off')
    ax1.set_aspect('equal', adjustable='box')

    # --- GRAFO B ---
    node_colors_B = []
    node_sizes_B = []
    labels_B = {}
    for n in nodes_B_no_added:
        if n in matched_nodes_B:
            color_match = node_to_color_B.get(n, 'red')
            node_colors_B.append(color_match)
            node_sizes_B.append(5)
            labels_B[n] = str(n)
        else:
            node_type = G_B.nodes[n].get('type', 'unknown')
            node_colors_B.append(FINAL_PLOT_NODE_COLOR_MAP.get(node_type, 'grey'))
            node_sizes_B.append(1)

    nx.draw_networkx_nodes(G_B, posB, nodelist=nodes_B_no_added,
                           node_size=node_sizes_B, node_color=node_colors_B,
                           ax=ax2, linewidths=0)

    edge_colors_B = []
    edge_widths_B = []
    for (u, v) in edges_B_no_added:
        if u in matched_nodes_B and v in matched_nodes_B:
            if (u in node_to_color_B and v in node_to_color_B and
                node_to_color_B[u] == node_to_color_B[v]):
                edge_colors_B.append(node_to_color_B[u])
            else:
                edge_colors_B.append('red')
            edge_widths_B.append(0.5)
        else:
            edge_colors_B.append('darkgrey')
            edge_widths_B.append(0.1)

    nx.draw_networkx_edges(G_B, posB, edgelist=edges_B_no_added,
                           edge_color=edge_colors_B, width=edge_widths_B, ax=ax2)
    nx.draw_networkx_labels(G_B, posB, labels=labels_B, font_size=0.5, font_color='black', ax=ax2)

    # Disegno la circonferenza B
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
