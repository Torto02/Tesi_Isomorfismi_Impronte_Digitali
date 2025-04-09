
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
    'unknown': 'grey' # Colore per tipi non specificati
}

# Mappa colori per plot finale (ora identica alla mappa standard per coerenza)
FINAL_PLOT_NODE_COLOR_MAP = NODE_TYPE_COLOR_MAP

def plot_and_save_subgraph(S, G_original, source_node, output_folder, filename):
    """
    Disegna il sottografo S (estratto da G_original) e lo salva.
    - Disegna solo archi non 'added'.
    - Colora i nodi base al loro 'type' usando NODE_TYPE_COLOR_MAP.
    - Evidenzia il nodo sorgente in giallo.
    - Aggiunge etichette (indici) ai nodi.
    """
    # Ottieni posizioni dal grafo originale G_original per coerenza
    pos = nx.get_node_attributes(G_original, 'pos')
    # Filtra posizioni solo per i nodi presenti in S
    pos_S = {node: p for node, p in pos.items() if node in S}

    if not pos_S:
        print(f"Attenzione: Nessuna posizione trovata per i nodi nel sottografo {filename}. Plot annullato.")
        return

    # Filtra archi "veri ridge" presenti in S
    true_ridge_edges = [(u, v) for u, v, data in S.edges(data=True)
                        if data.get('type') != 'added']

    # Costruisco la lista di colori corrispondente all'ordine dei nodi in S
    node_colors = []
    node_sizes = []
    node_list_S = list(S.nodes()) # Ottieni l'ordine dei nodi in S
    for n in node_list_S:
        node_data = S.nodes[n]
        tipo = node_data.get('type', 'unknown')
        # Usa la mappa colori del plot finale per coerenza visiva dove possibile
        node_colors.append(FINAL_PLOT_NODE_COLOR_MAP.get(tipo, 'grey'))
        # Dimensione standard per tutti i nodi
        node_sizes.append(15)

    plt.figure(figsize=(18, 9))
    ax = plt.gca() # Get current axes

    # Disegno i nodi con colore a seconda del tipo
    nx.draw_networkx_nodes(
        S, pos_S,
        nodelist=node_list_S,
        node_size=node_sizes,
        node_color=node_colors,
        linewidths=0.5, # Leggero bordo per chiarezza
        edgecolors='black',
        ax=ax
    )

    # Disegno solo gli archi "veri ridge"
    nx.draw_networkx_edges(
        S, pos_S,
        edgelist=true_ridge_edges,
        edge_color="grey",
        width=0.5,
        ax=ax
    )

    # Evidenzio il nodo sorgente (se presente)
    if source_node in S:
        nx.draw_networkx_nodes(
            S, pos_S,
            nodelist=[source_node],
            node_size=15,
            node_color="red", # Cambiato in rosso per maggior visibilità
            edgecolors='black', # Bordo per risaltare
            linewidths=1.0,
            ax=ax
        )

    # Label sui nodi (Indice del nodo) - MODIFICA: Riattivato
    nx.draw_networkx_labels(
        S, pos_S,
        labels={n: str(n) for n in node_list_S},
        font_size=0.5,  # Dimensione appropriata per sottografo
        font_color="black",
        ax=ax
    )

    plt.title(f"Sottografo attorno a nodo {source_node}")
    plt.axis("off")  # Disattiva gli assi per rimuovere le coordinate
    ax.set_aspect('equal', adjustable='box')  # Assicura proporzioni corrette

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
    - Usa posizioni dai grafi originali G_A e G_B.
    - Disegna solo archi non 'added'.
    - Colora nodi base al tipo (FINAL_PLOT_NODE_COLOR_MAP).
    - Evidenzia i nodi mappati (chiavi e valori di 'mapping') in rosso.
    - Aggiunge etichette (indici) ai nodi.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 9))

    # Ottieni posizioni dai grafi originali
    pos_A_orig = nx.get_node_attributes(G_A, 'pos')
    pos_B_orig = nx.get_node_attributes(G_B, 'pos')

    # Filtra posizioni per i nodi presenti nei sottografi
    pos_A = {node: p for node, p in pos_A_orig.items() if node in S_A}
    pos_B = {node: p for node, p in pos_B_orig.items() if node in S_B}

    if not pos_A or not pos_B:
        print(f"Attenzione: Posizioni mancanti per i nodi in {filename}. Plot annullato.")
        plt.close()
        return

    # --- Plot Sottografo A ---
    edges_A_no_added = [(u, v) for u, v, data in S_A.edges(data=True) if data.get('type') != 'added']
    node_list_A = list(S_A.nodes())

    # Colori e dimensioni per nodi
    node_colors_A = []
    node_sizes_A = []
    for n in node_list_A:
        if n in mapping.keys():
            node_colors_A.append('red')
            node_sizes_A.append(20) # Leggermente più grandi se mappati
        else:
            node_type = S_A.nodes[n].get('type', 'unknown')
            node_colors_A.append(FINAL_PLOT_NODE_COLOR_MAP.get(node_type, 'grey'))
            node_sizes_A.append(10) # Dimensione base

    # Colori e spessori archi
    edge_colors_A = []
    edge_widths_A = []
    for u, v in edges_A_no_added:
        if u in mapping.keys() and v in mapping.keys():
            edge_colors_A.append('red')
            edge_widths_A.append(0.7) # Più spessi se tra nodi mappati
        else:
            edge_colors_A.append('darkgrey')
            edge_widths_A.append(0.3)

    nx.draw_networkx_nodes(S_A, pos_A, nodelist=node_list_A, node_size=node_sizes_A,
                          node_color=node_colors_A, linewidths=0.5, edgecolors='black', ax=ax1)
    nx.draw_networkx_edges(S_A, pos_A, edgelist=edges_A_no_added,
                          edge_color=edge_colors_A, width=edge_widths_A, ax=ax1)
    # Label sui nodi (Indice del nodo) - Già presente
    nx.draw_networkx_labels(S_A, pos_A, labels={n: str(n) for n in node_list_A}, font_size=0.5, ax=ax1)

    # --- Plot Sottografo B ---
    edges_B_no_added = [(u, v) for u, v, data in S_B.edges(data=True) if data.get('type') != 'added']
    node_list_B = list(S_B.nodes())

    # Colori e dimensioni per nodi
    node_colors_B = []
    node_sizes_B = []
    for n in node_list_B:
        if n in mapping.values():
            node_colors_B.append('red')
            node_sizes_B.append(20)
        else:
            node_type = S_B.nodes[n].get('type', 'unknown')
            node_colors_B.append(FINAL_PLOT_NODE_COLOR_MAP.get(node_type, 'grey'))
            node_sizes_B.append(10)

    # Colori e spessori archi
    edge_colors_B = []
    edge_widths_B = []
    for u, v in edges_B_no_added:
        if u in mapping.values() and v in mapping.values():
            edge_colors_B.append('red')
            edge_widths_B.append(0.7)
        else:
            edge_colors_B.append('darkgrey')
            edge_widths_B.append(0.3)

    nx.draw_networkx_nodes(S_B, pos_B, nodelist=node_list_B, node_size=node_sizes_B,
                          node_color=node_colors_B, linewidths=0.5, edgecolors='black', ax=ax2)
    nx.draw_networkx_edges(S_B, pos_B, edgelist=edges_B_no_added,
                          edge_color=edge_colors_B, width=edge_widths_B, ax=ax2)
    # Label sui nodi (Indice del nodo) - Già presente
    nx.draw_networkx_labels(S_B, pos_B, labels={n: str(n) for n in node_list_B}, font_size=0.5, ax=ax2)

    ax1.set_title(f"Sottografo A (Match: {len(mapping)} nodi)")
    ax1.axis("off")  # Disattiva gli assi
    ax1.set_aspect('equal', adjustable='box')

    ax2.set_title(f"Sottografo B (Match: {len(mapping)} nodi)")
    ax2.axis("off")  # Disattiva gli assi
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
    centerA_coords, radiusA, # Posizione e raggio per il cerchio A
    centerB_coords, radiusB, # Posizione e raggio per il cerchio B
    output_folder, filename,
    all_matches=None  # Nuovo parametro: lista di dizionari con i match {'map': mapping, 'nodes_A': set(), 'nodes_B': set()}
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

    # Genera una lista di colori distinti per i diversi match
    import matplotlib.colors as mcolors
    # Usa colori predefiniti di matplotlib escludendo quelli troppo chiari
    match_colors = list(mcolors.TABLEAU_COLORS.values())  # 10 colori distinti
    # Aggiungi altri colori se necessario
    match_colors.extend(['darkred', 'darkblue', 'darkgreen', 'darkorange', 'darkviolet'])
    
    # Crea dizionari per mappare nodi ai colori dei loro match
    node_to_color_A = {}
    node_to_color_B = {}
    
    # Se abbiamo la lista dei match, assegna colori diversi a ciascun match
    if all_matches:
        for i, match_info in enumerate(all_matches):
            color_idx = i % len(match_colors)  # Riutilizza i colori se ci sono più match che colori
            color = match_colors[color_idx]
            
            # Assegna lo stesso colore a tutti i nodi di questo match
            for node_a in match_info['nodes_A']:
                node_to_color_A[node_a] = color
            for node_b in match_info['nodes_B']:
                node_to_color_B[node_b] = color

    # --- GRAFO A ---
    edges_A_no_added = [(u, v) for u, v, data in G_A.edges(data=True) if data.get('type') != 'added']
    nodes_A_list = list(G_A.nodes())

    # Colori e dimensioni default (non matchati)
    node_colors_A = []
    node_sizes_A = []
    labels_A = {}  # Dizionario per le etichette (solo nodi matchati)
    for n in nodes_A_list:
        if n in matched_nodes_A:
            # Usa il colore specifico del match se disponibile, altrimenti usa rosso
            node_colors_A.append(node_to_color_A.get(n, 'red'))
            node_sizes_A.append(5)  # Dimensione maggiore per matchati
            labels_A[n] = str(n)  # Aggiungi etichetta per nodo matchato
        else:
            node_type = G_A.nodes[n].get('type', 'unknown')
            node_colors_A.append(FINAL_PLOT_NODE_COLOR_MAP.get(node_type, 'grey'))
            node_sizes_A.append(1)  # Dimensione molto piccola per non matchati

    # Disegna tutti i nodi
    nx.draw_networkx_nodes(G_A, posA, nodelist=nodes_A_list, node_size=node_sizes_A, 
                          node_color=node_colors_A, ax=ax1, linewidths=0)

    # Colori e spessori archi
    edge_colors_A = []
    edge_widths_A = []
    for u, v in edges_A_no_added:
        if u in matched_nodes_A and v in matched_nodes_A:
            # Se entrambi i nodi appartengono allo stesso match, usa il loro colore
            if u in node_to_color_A and v in node_to_color_A and node_to_color_A[u] == node_to_color_A[v]:
                edge_colors_A.append(node_to_color_A[u])
            else:
                edge_colors_A.append('red')  # Default se non hanno lo stesso colore
            edge_widths_A.append(0.5)  # Spessore maggiore per matchati
        else:
            edge_colors_A.append('darkgrey')
            edge_widths_A.append(0.1)  # Spessore molto piccolo per non matchati

    # Disegna tutti gli archi (non 'added')
    nx.draw_networkx_edges(G_A, posA, edgelist=edges_A_no_added, edge_color=edge_colors_A, 
                          width=edge_widths_A, ax=ax1)

    # Disegna le etichette SOLO per i nodi matchati
    nx.draw_networkx_labels(G_A, posA, labels=labels_A, font_size=0.5, font_color='black', ax=ax1)

    # Disegna la circonferenza A
    if centerA_coords and radiusA:
        circleA = Circle(centerA_coords, radiusA, fill=False, edgecolor='blue', linewidth=1, linestyle='--')
        ax1.add_patch(circleA)

    ax1.set_title(f"Grafo A ({G_A.number_of_nodes()} nodi) - Match ({len(matched_nodes_A)}) colorati")
    ax1.axis('off')  # Disattiva gli assi
    ax1.set_aspect('equal', adjustable='box')

    # --- GRAFO B (logica simile ad A) ---
    edges_B_no_added = [(u, v) for u, v, data in G_B.edges(data=True) if data.get('type') != 'added']
    nodes_B_list = list(G_B.nodes())

    node_colors_B = []
    node_sizes_B = []
    labels_B = {}  # Dizionario etichette B
    for n in nodes_B_list:
        if n in matched_nodes_B:
            # Usa il colore specifico del match se disponibile, altrimenti usa rosso
            node_colors_B.append(node_to_color_B.get(n, 'red'))
            node_sizes_B.append(5)
            labels_B[n] = str(n)  # Aggiungi etichetta B
        else:
            node_type = G_B.nodes[n].get('type', 'unknown')
            node_colors_B.append(FINAL_PLOT_NODE_COLOR_MAP.get(node_type, 'grey'))
            node_sizes_B.append(1)

    nx.draw_networkx_nodes(G_B, posB, nodelist=nodes_B_list, node_size=node_sizes_B, 
                          node_color=node_colors_B, ax=ax2, linewidths=0)

    edge_colors_B = []
    edge_widths_B = []
    for u, v in edges_B_no_added:
        if u in matched_nodes_B and v in matched_nodes_B:
            # Se entrambi i nodi appartengono allo stesso match, usa il loro colore
            if u in node_to_color_B and v in node_to_color_B and node_to_color_B[u] == node_to_color_B[v]:
                edge_colors_B.append(node_to_color_B[u])
            else:
                edge_colors_B.append('red')  # Default se non hanno lo stesso colore
            edge_widths_B.append(0.5)
        else:
            edge_colors_B.append('darkgrey')
            edge_widths_B.append(0.1)

    nx.draw_networkx_edges(G_B, posB, edgelist=edges_B_no_added, edge_color=edge_colors_B, 
                          width=edge_widths_B, ax=ax2)

    # Disegna le etichette SOLO per i nodi matchati B
    nx.draw_networkx_labels(G_B, posB, labels=labels_B, font_size=0.5, font_color='black', ax=ax2)

    # Disegna la circonferenza B
    if centerB_coords and radiusB:
        circleB = Circle(centerB_coords, radiusB, fill=False, edgecolor='blue', linewidth=1, linestyle='--')
        ax2.add_patch(circleB)

    ax2.set_title(f"Grafo B ({G_B.number_of_nodes()} nodi) - Match ({len(matched_nodes_B)}) colorati")
    ax2.axis('off')  # Disattiva gli assi
    ax2.set_aspect('equal', adjustable='box')

    plt.tight_layout()
    os.makedirs(output_folder, exist_ok=True)
    out_path = os.path.join(output_folder, filename)
    try:
        plt.savefig(out_path, dpi=800)  # DPI più alto per il finale
        print(f"Stampa finale dei grafi salvata in: {out_path}")
    except Exception as e:
        print(f"Errore durante il salvataggio di {out_path}: {e}")
    plt.close()