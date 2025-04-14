# matching.py
import networkx as nx
import math # Necessario per atan2 e degrees

# --- Funzioni per la valutazione della similarità ---

def is_cost_similar(cA, cB, threshold=0.5): # Soglia esempio 0.5
    """
    Verifica se due costi (M1) sono abbastanza simili in valore relativo.
    threshold: Massima differenza relativa permessa rispetto al valore più grande.
    """
    # Gestione esplicita degli infiniti
    if cA == float('inf') and cB == float('inf'):
        return True # Due infiniti sono considerati "simili"
    if cA == float('inf') or cB == float('inf'):
        return False # Infinito non è simile a un valore finito

    # Se entrambi finiti e molto piccoli (vicini a zero)
    # Aumentata tolleranza per M1 che ha costi bassi (0.0001)
    if abs(cA) < 1e-6 and abs(cB) < 1e-6:
        return True # Considera simili due costi quasi nulli

    # Calcolo differenza relativa
    denom = max(abs(cA), abs(cB))
    # Evita divisione per zero se entrambi sono zero (già gestito sopra)
    # o se il denominatore è estremamente piccolo
    if denom < 1e-9:
         return True

    try:
        diff_rel = abs(float(cA) - float(cB)) / denom
        return diff_rel <= threshold
    except (ValueError, TypeError):
        print(f"Attenzione: Valori non numerici in is_cost_similar: {cA}, {cB}")
        return False

def is_ridge_jump_similar(jumpA, jumpB, max_diff=1):
    """
    Verifica se la differenza nella metrica M_scavalcamenti è sotto una soglia assoluta.
    """
    # Gestione esplicita degli infiniti
    if jumpA == float('inf') and jumpB == float('inf'):
        return True
    if jumpA == float('inf') or jumpB == float('inf'):
        return False

    # Se entrambi finiti, calcola la differenza assoluta
    try:
        diff = abs(float(jumpA) - float(jumpB))
        return diff <= max_diff
    except (ValueError, TypeError):
        print(f"Attenzione: Valori non numerici in is_ridge_jump_similar: {jumpA}, {jumpB}")
        return False

def calculate_angle(pos1, pos2):
    """
    Calcola l'angolo (in gradi) del vettore da pos1 a pos2 rispetto all'asse x positivo.
    pos1, pos2: tuple (x, y)
    Ritorna l'angolo in gradi [0, 360).
    """
    try:
        dx = pos2[0] - pos1[0]
        dy = pos2[1] - pos1[1]
        # Evita errore se i punti coincidono
        if dx == 0 and dy == 0:
            return 0.0 # O None, o gestisci come preferisci
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad)
        # Normalizza l'angolo a [0, 360)
        return angle_deg % 360
    except (TypeError, IndexError):
        print(f"Errore: Posizioni non valide per calcolo angolo: {pos1}, {pos2}")
        return None # Ritorna None se le posizioni non sono valide

def is_angle_similar(angleA, angleB, tolerance_degrees=30): # Tolleranza esempio 30 gradi
    """
    Verifica se due angoli (in gradi) sono simili entro una tolleranza,
    gestendo il wraparound (es. 350 gradi è vicino a 10 gradi).
    """
    if angleA is None or angleB is None:
        return False # Non simili se uno degli angoli non è calcolabile

    try:
        angleA_f = float(angleA)
        angleB_f = float(angleB)
        # Differenza angolare assoluta
        diff = abs(angleA_f - angleB_f)
        # Gestione del wraparound a 360 gradi
        # La differenza minima tra due angoli è min(diff, 360 - diff)
        angular_distance = min(diff, 360.0 - diff)
        return angular_distance <= tolerance_degrees
    except (ValueError, TypeError):
        print(f"Attenzione: Valori non numerici in is_angle_similar: {angleA}, {angleB}")
        return False


# --- Algoritmo di Matching Ricorsivo ---

def match_subgraphs(
    G_A, G_B,                      # I sottografi (indotti) da confrontare
    M1_A,                          # Matrice M1 (costo shortest path) di A
    M1_B,                          # Matrice M1 (costo shortest path) di B
    M_scavalcamenti_A,             # Matrice Scavalcamenti per A
    M_scavalcamenti_B,             # Matrice Scavalcamenti per B
    nodeA, nodeB,                  # Nodi di partenza per il matching
    mapping=None,                  # Dizionario per tracciare i nodi mappati {nodeA: nodeB}
    visited_pairs=None,            # Set per evitare cicli infiniti nella ricorsione {(nodeA, nodeB)}
    cost_threshold_rel=0.5,        # Soglia per is_cost_similar (M1)
    max_ridge_diff=1,              # Soglia per is_ridge_jump_similar (M_scavalcamenti)
    angle_tolerance_degrees=30     # Soglia per is_angle_similar
):
    """
    Tenta il match ricorsivo di G_A e G_B partendo da (nodeA, nodeB).

    Verifica:
    1) Tipo di nodo ('type').
    2) Compatibilità mapping.
    3) Ricorsione sui vicini verificando:
       - Similarità Scavalcamenti (M_scavalcamenti) [max_ridge_diff]
       - Similarità Costo M1 [cost_threshold_rel]
       - Similarità Angolo tra vettori (node -> neighbor) [angle_tolerance_degrees]

    Ritorna True se il matching ricorsivo ha successo, altrimenti False.
    Il mapping viene aggiornato inplace.
    """

    if mapping is None: mapping = {}
    if visited_pairs is None: visited_pairs = set()

    if (nodeA, nodeB) in visited_pairs: return True
    visited_pairs.add((nodeA, nodeB))

    # 1) Controllo Tipi di Nodo
    try:
        typeA = G_A.nodes[nodeA].get('type')
        typeB = G_B.nodes[nodeB].get('type')
        if typeA != typeB: return False
    except KeyError:
         print(f"Errore: Chiave 'type' mancante per nodo {nodeA} o {nodeB}.")
         return False

    # 2) Controllo Coerenza Mapping
    if nodeA in mapping and mapping[nodeA] != nodeB: return False
    for existing_a, existing_b in mapping.items():
        if existing_b == nodeB and existing_a != nodeA: return False

    mapping[nodeA] = nodeB

    # 3) Ricorsione DFS Parallelo sui Vicini *all'interno dei sottografi*
    neighborsA = list(G_A.neighbors(nodeA))
    neighborsB = list(G_B.neighbors(nodeB))

    for nA in neighborsA:
        found_match_for_nA = False
        potential_matches_for_nA = [
            nB for nB in neighborsB
            if (nB not in mapping.values() or mapping.get(nA) == nB)
        ]

        for nB in potential_matches_for_nA:
            # Assumiamo che nodeA, nA, nodeB, nB siano indici/chiavi valide per le matrici
            # e che abbiano l'attributo 'pos' nel grafo.

            # --- Check Scavalcamenti (M_scavalcamenti) ---
            try:
                scavalcamenti_A = M_scavalcamenti_A[nodeA][nA]
                scavalcamenti_B = M_scavalcamenti_B[nodeB][nB]
                if not is_ridge_jump_similar(scavalcamenti_A, scavalcamenti_B, max_ridge_diff):
                    continue # Prova prossimo nB
            except (IndexError, KeyError):
                 # print(f"Warn: Accesso M_scavalcamenti fallito per ({nodeA},{nA}) o ({nodeB},{nB}).")
                 continue

            # --- Check M1 Cost ---
            try:
                cost_M1_A = M1_A[nodeA][nA]
                cost_M1_B = M1_B[nodeB][nB]
                if not is_cost_similar(cost_M1_A, cost_M1_B, cost_threshold_rel):
                    # print(f"Fail M1 Cost ({nodeA}-{nA} vs {nodeB}-{nB}): {cost_M1_A:.4f} vs {cost_M1_B:.4f}") # Debug
                    continue # Prova prossimo nB
            except (IndexError, KeyError):
                 # print(f"Warn: Accesso M1 fallito per ({nodeA},{nA}) o ({nodeB},{nB}).")
                 continue

            # --- Check Angle ---
            try:
                pos_nodeA = G_A.nodes[nodeA]['pos']
                pos_nA = G_A.nodes[nA]['pos']
                pos_nodeB = G_B.nodes[nodeB]['pos']
                pos_nB = G_B.nodes[nB]['pos']

                angle_A = calculate_angle(pos_nodeA, pos_nA)
                angle_B = calculate_angle(pos_nodeB, pos_nB)

                if not is_angle_similar(angle_A, angle_B, angle_tolerance_degrees):
                    # print(f"Fail Angle ({nodeA}-{nA} vs {nodeB}-{nB}): {angle_A:.1f} vs {angle_B:.1f}") # Debug
                    continue # Prova prossimo nB
            except KeyError:
                 # print(f"Warn: Posizione mancante per nodi ({nodeA},{nA}) o ({nodeB},{nB}) per angolo.")
                 continue
            except Exception as e:
                 # print(f"Warn: Errore generico calcolo angolo: {e}")
                 continue


            # Se tutti i check passano, tenta la ricorsione
            if match_subgraphs(
                G_A, G_B,
                M1_A, M1_B, # Passa M1
                M_scavalcamenti_A, M_scavalcamenti_B,
                nA, nB, # Prossima coppia
                mapping, visited_pairs.copy(),
                cost_threshold_rel, # Passa soglia M1
                max_ridge_diff,
                angle_tolerance_degrees # Passa soglia angolo
            ):
                found_match_for_nA = True
                break # Trovato match per nA, passa al prossimo vicino di nodeA

        if not found_match_for_nA:
            # Backtrack
            del mapping[nodeA]
            return False

    # Se siamo arrivati qui, tutti i vicini di nodeA hanno trovato un partner
    return True
