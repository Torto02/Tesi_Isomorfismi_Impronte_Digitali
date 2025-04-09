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