# --- Funzioni per la valutazione della similarità ---

def is_cost_similar(cA, cB, threshold=1.5):
    """
    Verifica se due costi (M1 o M2) sono abbastanza simili in valore relativo.
    Permette una soglia più lasca per gestire imprecisioni.
    threshold=0.1 è molto stringente, 1.5 permette differenze maggiori.
    """
    # Gestione esplicita degli infiniti
    if cA == float('inf') and cB == float('inf'):
        return True # Due infiniti sono considerati "simili" in questo contesto
    if cA == float('inf') or cB == float('inf'):
        return False # Infinito non è simile a un valore finito

    # Se entrambi finiti e molto piccoli (vicini a zero)
    if abs(cA) < 1e-9 and abs(cB) < 1e-9:
        return True # Considera simili due costi quasi nulli

    # Calcolo differenza relativa
    denom = max(abs(cA), abs(cB))
    if denom < 1e-9: # Evita divisione per zero se entrambi sono zero (già gestito sopra)
         return True
    diff = abs(cA - cB) / denom

    return diff <= threshold

def is_ridge_jump_similar(jumpA, jumpB, max_diff=2):
    """
    Verifica se la differenza in M4 (numero di salti/ridge jumps) è sotto una soglia.
    """
    # Gestione esplicita degli infiniti
    if jumpA == float('inf') and jumpB == float('inf'):
        return True
    if jumpA == float('inf') or jumpB == float('inf'):
        return False

    # Se entrambi finiti, calcola la differenza assoluta
    return abs(jumpA - jumpB) <= max_diff

# --- Algoritmo di Matching Ricorsivo ---
import math

def check_transform_is_ok(G_A, G_B, current_mapping,
                         max_rotation_deg=80,
                         allow_reflection=False):
    """
    Verifica se la trasformazione che mappa i nodi di G_A in quelli di G_B
    (secondo `current_mapping`) non introduce riflessione (se allow_reflection=False)
    e non ha rotazioni superiori a 'max_rotation_deg' gradi.

    Ritorna True se la trasformazione è "accettabile", False altrimenti.
    """

    # Se il mapping ha pochissimi nodi, spesso non ha senso parlare di rotazione/riflessione.
    # Magari, se < 3 nodi, lo accettiamo direttamente senza test
    if len(current_mapping) < 3:
        return True

    # 1) Estrai le posizioni in liste parallele
    A_points = []
    B_points = []
    for a_node, b_node in current_mapping.items():
        posA = G_A.nodes[a_node].get('pos')
        posB = G_B.nodes[b_node].get('pos')
        if not posA or not posB:
            # Se manca una posizione, ignoriamo il test e accettiamo (oppure scartiamo)
            return True
        A_points.append(posA)
        B_points.append(posB)

    # 2) Calcola i centroidi (media delle coordinate)
    def centroid(pts):
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        return (cx, cy)

    cA = centroid(A_points)
    cB = centroid(B_points)

    # 3) Calcola i vettori (dal centroide) e le loro norme
    def vec_sub(p1, p2):
        return (p1[0] - p2[0], p1[1] - p2[1])

    A_vecs = [vec_sub(p, cA) for p in A_points]
    B_vecs = [vec_sub(p, cB) for p in B_points]

    # Per capire se c'è riflessione, guardiamo il segno delle aree di triangoli
    # in A vs B (un modo veloce per vedere se c'è un flip di orientamento).
    # Ad esempio prendiamo triplette (0, i, i+1) se i+1 < len(A_vecs).
    # Calcoliamo cross(A_vecs[i], A_vecs[i+1]) e cross(B_vecs[i], B_vecs[i+1]) e confrontiamo il segno.
    def cross_z(v1, v2):
        # Restituisce la componente z del prodotto vettoriale 2D (x1*y2 - y1*x2)
        return v1[0]*v2[1] - v1[1]*v2[0]

    sign_mismatches = 0
    total_checked = 0
    for i in range(1, len(A_vecs)-1):
        ca = cross_z(A_vecs[i], A_vecs[i+1])
        cb = cross_z(B_vecs[i], B_vecs[i+1])
        if ca != 0 and cb != 0:
            # Se uno dei due è zero, è triangolo degenerato, non lo contiamo
            total_checked += 1
            if (ca * cb) < 0:
                # Hanno segni opposti => riflessione su questo triangolo
                sign_mismatches += 1

    # Se più della metà dei triangoli ha segno opposto, è molto probabilmente una riflessione
    if not allow_reflection and total_checked > 0:
        fraction = sign_mismatches / total_checked
        if fraction > 0.5:
            # troppa differenza di segno => riflessione netta
            return False

    # 4) Calcolo dell’angolo medio di rotazione (un metodo semplificato):
    #    Confrontiamo l’angolo dei vettori in B con quelli corrispondenti in A.
    #    Cerchiamo la "miglior" differenza angolare media, poi verifichiamo se è > soglia.

    def vec_angle(v):
        # Restituisce l'angolo in [0, 2π) del vettore v rispetto all'asse x
        return math.atan2(v[1], v[0]) if (v[0] != 0 or v[1] != 0) else 0

    A_angles = [vec_angle(v) for v in A_vecs]
    B_angles = [vec_angle(v) for v in B_vecs]

    # Possiamo calcolare differenze e poi "normalizzarle" in -π..+π
    # e prenderne la media. Ovviamente, un matching perfetto (senza riflessioni)
    # si dovrebbe allineare con differenza ~ costante.
    diffs = []
    for a_ang, b_ang in zip(A_angles, B_angles):
        diff = b_ang - a_ang
        # Normalizza in -π..+π
        while diff > math.pi:
            diff -= 2*math.pi
        while diff <= -math.pi:
            diff += 2*math.pi
        diffs.append(diff)

    # Ora prendiamo la media
    avg_diff = sum(diffs)/len(diffs)
    # Convertiamo in gradi
    avg_diff_deg = abs(avg_diff * 180.0 / math.pi)

    if avg_diff_deg > max_rotation_deg:
        # Rotazione media troppo ampia => scarta
        return False

    return True



def match_subgraphs(
    G_A, G_B,            # I sottografi (indotti) da confrontare
    M1_A, M2_A, M4_A,    # Matrici dell'impronta A originale
    M1_B, M2_B, M4_B,    # Matrici dell'impronta B originale
    nodeA, nodeB,        # Nodi di partenza per il matching
    mapping=None,        # Dizionario per tracciare i nodi mappati {nodeA: nodeB}
    visited_pairs=None,  # Set per evitare cicli infiniti nella ricorsione {(nodeA, nodeB)}
    cost_threshold_rel=0.5, # Soglia per is_cost_similar (differenza relativa)
    max_ridge_diff=2      # Soglia per is_ridge_jump_similar (differenza assoluta)
):
    """
    Tenta di effettuare il match (allineamento) ricorsivo di due sottografi G_A e G_B,
    partendo dalla coppia (nodeA, nodeB). Verifica:
      1) Tipo di nodo.
      2) Compatibilità del mapping corrente.
      3) Ricorsione sui vicini *all'interno dei sottografi G_A e G_B*,
         verificando la similarità dei costi (M1, M2) e dei salti (M4)
         *usando i valori dalle matrici originali*.

    Ritorna True se il matching ricorsivo ha successo a partire da (nodeA, nodeB),
    altrimenti False. Il mapping viene aggiornato inplace.
    """

    if mapping is None:
        mapping = {}
    if visited_pairs is None:
        visited_pairs = set()

    # Controllo anti-ciclo: se abbiamo già visitato questa coppia, OK (non fallire)
    if (nodeA, nodeB) in visited_pairs:
        return True
    visited_pairs.add((nodeA, nodeB))

    # 1) Controllo Tipi di Nodo: Devono essere uguali
    typeA = G_A.nodes[nodeA].get('type')
    typeB = G_B.nodes[nodeB].get('type')
    if typeA != typeB:
        # print(f"Fallimento tipo: {nodeA}({typeA}) != {nodeB}({typeB})") # Debug
        return False

    # 2) Controllo Coerenza Mapping:
    #    - Se nodeA è già mappato, deve essere mappato a nodeB.
    #    - Se nodeB è già mappato, deve essere mappato da nodeA.
    if nodeA in mapping and mapping[nodeA] != nodeB:
        # print(f"Fallimento mapping: {nodeA} già mappato a {mapping[nodeA]}, non a {nodeB}") # Debug
        return False
    # Controlla anche l'inverso per sicurezza (se B è già la destinazione di un altro A')
    # Questo previene mapping molti-a-uno o uno-a-molti
    for existing_a, existing_b in mapping.items():
        if existing_b == nodeB and existing_a != nodeA:
             # print(f"Fallimento mapping: {nodeB} già mappato da {existing_a}, non da {nodeA}") # Debug
             return False

    # Se i controlli passano, aggiorna il mapping
    mapping[nodeA] = nodeB

    # 3) Ricorsione DFS Parallelo sui Vicini *all'interno dei sottografi*
    neighborsA = list(G_A.neighbors(nodeA))
    neighborsB = list(G_B.neighbors(nodeB))

    # Tentiamo di trovare un partner valido in B per ogni vicino di A
    for nA in neighborsA:
        found_match_for_nA = False
        # Potenziali candidati per nA tra i vicini di nodeB
        potential_matches_for_nA = [nB for nB in neighborsB
                                    if nB not in mapping.values() or mapping.get(nA) == nB]

        for nB in potential_matches_for_nA:
            # Controlla la similarità delle metriche M1, M2, M4 tra (nodeA, nA) e (nodeB, nB)
            # **Usando le matrici globali** perché contengono le distanze complete
            # Otteniamo gli indici corrispondenti se necessario (se i nodi non sono 0..N-1)
            # Assumiamo qui che i nodi siano usabili direttamente come indici per semplicità
            # Se non lo sono, serve una mappa nodi -> indici passata dall'esterno

            # --- Check M1 ---
            cost_M1_A = M1_A[nodeA][nA]
            cost_M1_B = M1_B[nodeB][nB]
            if not is_cost_similar(cost_M1_A, cost_M1_B, cost_threshold_rel):
                # print(f"Fail M1 ({nodeA}-{nA} vs {nodeB}-{nB}): {cost_M1_A:.2f} vs {cost_M1_B:.2f}") # Debug
                continue

            # --- Check M2 ---
            cost_M2_A = M2_A[nodeA][nA]
            cost_M2_B = M2_B[nodeB][nB]
            if not is_cost_similar(cost_M2_A, cost_M2_B, cost_threshold_rel):
                # print(f"Fail M2 ({nodeA}-{nA} vs {nodeB}-{nB}): {cost_M2_A:.2f} vs {cost_M2_B:.2f}") # Debug
                continue

            # --- Check M4 ---
            jump_M4_A = M4_A[nodeA][nA]
            jump_M4_B = M4_B[nodeB][nB]
            if not is_ridge_jump_similar(jump_M4_A, jump_M4_B, max_ridge_diff):
                # print(f"Fail M4 ({nodeA}-{nA} vs {nodeB}-{nB}): {jump_M4_A} vs {jump_M4_B}") # Debug
                continue

            # Se le metriche sono simili, tenta la ricorsione
            # Passa una copia del visited_pairs per evitare interferenze tra rami diversi della ricerca
            if match_subgraphs(
                G_A, G_B,
                M1_A, M2_A, M4_A,
                M1_B, M2_B, M4_B,
                nA, nB, mapping, visited_pairs.copy(), # Usa copia di visited
                cost_threshold_rel, max_ridge_diff
            ):
                found_match_for_nA = True
                break # Trovato un match per nA, passa al prossimo vicino di nodeA

        # Se, dopo aver provato tutti i vicini di nodeB, non abbiamo trovato
        # un partner valido per nA, allora il matching a partire da (nodeA, nodeB) fallisce.
        if not found_match_for_nA:
            # Backtrack: Rimuovi il mapping corrente (nodeA -> nodeB) perché non porta a una soluzione completa
            del mapping[nodeA]
            # print(f"Fallimento ricorsivo: non trovato match per {nA} partendo da {nodeA}-{nodeB}") # Debug
            return False

    # Se siamo arrivati qui, tutti i vicini di nodeA hanno trovato un partner
    # e la ricorsione è andata a buon fine per tutti.
    return True
