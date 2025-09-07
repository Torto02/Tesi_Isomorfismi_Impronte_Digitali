import json
import networkx as nx
import matplotlib.pyplot as plt
import os

def choose_impronte(impronte):
    print("Impronte disponibili:")
    for i, name in enumerate(impronte, start=1):
        print(f"  {i}: {name}")
    s = input("\nSeleziona impronte da plottare (numeri separati da ',' , intervalli '1-3', nomi, 'all' per tutte). Premi Invio per annullare: ").strip()
    if not s:
        return []
    if s.lower() in ('all', 'tutte'):
        return impronte
    tokens = [t.strip() for t in s.split(',') if t.strip()]
    selected_idx = set()
    for t in tokens:
        if '-' in t:
            parts = t.split('-', 1)
            try:
                a = int(parts[0])
                b = int(parts[1])
                if a <= b:
                    # convert to 0-based, inclusive
                    selected_idx.update(range(max(0, a-1), min(len(impronte), b)))
            except ValueError:
                # maybe a name with hyphen
                if t in impronte:
                    selected_idx.add(impronte.index(t))
        elif t.isdigit():
            idx = int(t) - 1
            if 0 <= idx < len(impronte):
                selected_idx.add(idx)
        else:
            if t in impronte:
                selected_idx.add(impronte.index(t))
            else:
                print(f"Nome non riconosciuto: '{t}' (ignorato)")
    return [impronte[i] for i in sorted(selected_idx)]

def main():
    # Flag per mostrare o meno i nodi/archi "added"
    SHOW_ADDED = True

    # Percorso della cartella contenente le impronte
    folder_path = "/Users/riccardotortorelli/Desktop/Tesi/Archivio"
    output_folder = "/Users/riccardotortorelli/Desktop/Tesi/ImpronteGraphs"
    os.makedirs(output_folder, exist_ok=True)

    # Verifica che la cartella esista
    if not os.path.exists(folder_path):
        print("Errore: La cartella specificata non esiste.")
        return

    # Lista le impronte disponibili nella cartella
    impronte_disponibili = sorted([d for d in os.listdir(folder_path)
                               if os.path.isdir(os.path.join(folder_path, d))])

    # Se non ci sono impronte disponibili, esci
    if not impronte_disponibili:
        print("Nessuna impronta trovata nella cartella specificata.")
        return

    print(f"Trovate {len(impronte_disponibili)} impronte.")

    # Chiedi all'utente quali plottare
    selected = choose_impronte(impronte_disponibili)
    if not selected:
        print("Nessuna impronta selezionata. Uscita.")
        return

    print(f"Inizio il plot delle {len(selected)} impronte selezionate...")

    for impronta_selezionata in selected:
        impronta_path = os.path.join(folder_path, impronta_selezionata)
        nodes_file = os.path.join(impronta_path, "nodes_graph.json")
        edges_file = os.path.join(impronta_path, "edges_graph.json")

        if not os.path.exists(nodes_file) or not os.path.exists(edges_file):
            print(f"Errore: File nodes_graph.json o edges_graph.json non trovati in {impronta_path}.")
            continue

        with open(nodes_file, 'r') as f:
            nodes_data = json.load(f)
        with open(edges_file, 'r') as f:
            edges_data = json.load(f)

        nodes = nodes_data['nodes']
        edges = edges_data['edges']

        G = nx.Graph()
        for i, node in enumerate(nodes):
            pos = tuple(node.get('coordinates', [0, 0]))
            ntype = node.get('type', 'unknown')
            G.add_node(i, pos=pos, type=ntype)

        for edge in edges:
            node1, node2 = edge['nodes']
            etype = edge.get('type', 'edge')
            dist = edge.get('distance', None)
            if node1 < len(nodes) and node2 < len(nodes):
                G.add_edge(node1, node2, type=etype, distance=dist)
            else:
                print(f"Attenzione: arco con nodi {edge['nodes']} non valido.")

        pos = nx.get_node_attributes(G, 'pos')

        node_color_map = {
            'ending': "#3fc700",
            'bifurcation': "#0084f8",
            'border': 'purple',
            'added': "#db7800"
        }
        edge_color_map = {
            'ridge': 'blue',
            'border': 'purple',
            'added': 'red'  # esplicito per gli archi added
        }

        if not SHOW_ADDED:
            nodes_to_draw = list(G.nodes())
            pos_filtered = pos
            node_colors = [node_color_map.get(G.nodes[n].get('type'), 'red') for n in G.nodes()]
            edges_to_draw = [(u, v) for u, v, attr in G.edges(data=True)
                            if attr.get('type') != 'added' and u in pos_filtered and v in pos_filtered]
            edge_colors = [edge_color_map.get(attr.get('type'), 'red')
                        for u, v, attr in G.edges(data=True)
                        if attr.get('type') != 'added' and u in pos_filtered and v in pos_filtered]
        else:
            nodes_to_draw = list(G.nodes())
            pos_filtered = pos
            node_colors = [node_color_map.get(G.nodes[n].get('type'), 'red') for n in G.nodes()]
            edges_to_draw = [(u, v) for u, v, attr in G.edges(data=True)]
            edge_colors = [edge_color_map.get(attr.get('type'), 'red') for u, v, attr in G.edges(data=True)]

        plt.figure(figsize=(15, 12))
        nx.draw_networkx_nodes(G, pos_filtered, nodelist=nodes_to_draw, node_color=node_colors, node_size=2)
        nx.draw_networkx_edges(G, pos_filtered, edgelist=edges_to_draw, edge_color=edge_colors, width=0.3)
        nx.draw_networkx_labels(G, pos_filtered, labels={n: n for n in nodes_to_draw}, font_size=1, font_color='black')

        plt.axis('off')
        plt.tight_layout()
        output_path = os.path.join(output_folder, f"{impronta_selezionata}_graph.png")
        plt.savefig(output_path, dpi=800)
        plt.close()
        print(f"Grafo di '{impronta_selezionata}' salvato in '{output_path}'.")

    print("\nTutti i grafi selezionati sono stati plottati e salvati nella cartella ImpronteGraphs.")

if __name__ == "__main__":
    main()
