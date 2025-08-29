
import networkx as nx
import math
from collections import deque
from typing import Dict, List, Tuple, Optional


class GraphMatcher:
    """Classe unificata per il matching tra sottografi con controlli rigorosi."""
    
    def __init__(self, G_A: nx.Graph, G_B: nx.Graph, M3_A, M3_B, 
                 M_scav_A, M_scav_B, angle_tolerance: float = 30.0,
                 max_ridge_diff: int = 1, max_edge_length_ratio: float = 3.0,
                 chirality_threshold: Optional[float] = None):
        self.G_A = G_A
        self.G_B = G_B
        self.M3_A = M3_A
        self.M3_B = M3_B
        self.M_scav_A = M_scav_A
        self.M_scav_B = M_scav_B
        self.angle_tolerance = angle_tolerance
        self.max_ridge_diff = max_ridge_diff
        self.max_edge_length_ratio = max_edge_length_ratio
        self.chirality_threshold = chirality_threshold
        
        # Cache per ottimizzazione
        self._ensure_caches()
    
    def _ensure_caches(self):
        """Costruisce tutte le cache necessarie una sola volta."""
        self._cache_real_neighbors(self.G_A)
        self._cache_real_neighbors(self.G_B)
        self._cache_node_indices(self.G_A)
        self._cache_node_indices(self.G_B)
    
    def _cache_real_neighbors(self, G: nx.Graph):
        """Cache dei vicini reali raggiungibili via nodi added."""
        if '_real_neighbor_cache' in G.graph:
            return
            
        cache = {}
        real_nodes = [n for n in G.nodes if G.nodes[n].get('type') != 'added']
        
        for src in real_nodes:
            reached = set()
            visited = {src}
            queue = deque([src])
            
            while queue:
                current = queue.popleft()
                for neighbor in G.neighbors(current):
                    if neighbor in visited:
                        continue
                    visited.add(neighbor)
                    
                    if G.nodes[neighbor].get('type') != 'added':
                        reached.add(neighbor)
                    else:
                        queue.append(neighbor)
            
            reached.discard(src)
            cache[src] = list(reached)
        
        G.graph['_real_neighbor_cache'] = cache
    
    def _cache_node_indices(self, G: nx.Graph):
        """Cache per mappatura nodi -> indici matrici."""
        if '_node2idx' not in G.graph:
            idx2node = list(G.nodes())
            node2idx = {n: i for i, n in enumerate(idx2node)}
            G.graph['_node2idx'] = node2idx
            G.graph['_idx2node'] = idx2node
    
    def get_real_neighbors(self, G: nx.Graph, node: int) -> List[int]:
        """Ottiene vicini reali (cachati)."""
        return G.graph['_real_neighbor_cache'].get(node, [])
    
    def is_real_node(self, G: nx.Graph, node: int) -> bool:
        """Verifica se un nodo è reale."""
        return G.nodes[node].get('type') != 'added'
    
    def get_real_nodes(self, G: nx.Graph) -> List[int]:
        """Ottiene tutti i nodi reali."""
        return [n for n in G.nodes() if self.is_real_node(G, n)]
    
    def get_connection_pattern(self, G: nx.Graph, u: int, v: int) -> str:
        """Classifica il tipo di connessione tra due nodi reali."""
        # Arco diretto
        if G.has_edge(u, v):
            return "edge_added" if G.edges[u, v].get("type") == "added" else "direct"
        
        # Percorso via nodo added
        for w in G.neighbors(u):
            if (G.nodes[w].get("type") == "added" and 
                G.edges[u, w].get("type") != "added" and
                G.has_edge(w, v) and 
                G.edges[w, v].get("type") != "added"):
                return "via_node"
        
        return "none"
    
    def calculate_angle(self, pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
        """Calcola angolo tra due punti in gradi."""
        dx, dy = pos2[0] - pos1[0], pos2[1] - pos1[1]
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            return 0.0
        return math.degrees(math.atan2(dy, dx)) % 360
    
    def find_path_via_added(self, G: nx.Graph, source: int, target: int) -> Optional[List[int]]:
        """Trova percorso minimo via nodi added."""
        visited = {source}
        queue = deque([[source]])
        
        while queue:
            path = queue.popleft()
            node = path[-1]
            
            if node == target:
                return path
                
            for neighbor in G.neighbors(node):
                if neighbor in visited:
                    continue
                if self.is_real_node(G, neighbor) and neighbor != target:
                    continue
                    
                visited.add(neighbor)
                queue.append(path + [neighbor])
        
        return None
    
    def get_angle_along_path(self, G: nx.Graph, source: int, target: int) -> Optional[float]:
        """Calcola angolo lungo il percorso tra due nodi."""
        if G.has_edge(source, target):
            return self.calculate_angle(G.nodes[source]['pos'], G.nodes[target]['pos'])
        
        path = self.find_path_via_added(G, source, target)
        if path and len(path) >= 2:
            return self.calculate_angle(G.nodes[path[0]]['pos'], G.nodes[path[-1]]['pos'])
        
        return None
    
    def check_structural_compatibility(self, nodes_A: List[int], nodes_B: List[int]) -> bool:
        """Controlli strutturali rapidi prima del matching dettagliato."""
        if len(nodes_A) != len(nodes_B):
            return False
        
        # Compatibilità tipi di nodi
        types_A = sorted(self.G_A.nodes[n]['type'] for n in nodes_A)
        types_B = sorted(self.G_B.nodes[n]['type'] for n in nodes_B)
        if types_A != types_B:
            return False
        
        # Compatibilità gradi
        degrees_A = sorted(len(self.get_real_neighbors(self.G_A, n)) for n in nodes_A)
        degrees_B = sorted(len(self.get_real_neighbors(self.G_B, n)) for n in nodes_B)
        if degrees_A != degrees_B:
            return False
        
        return True
    
    def build_candidate_map(self, nodes_A: List[int], nodes_B: List[int]) -> Dict[int, List[int]]:
        """Costruisce mappa di candidati compatibili per ogni nodo A."""
        degree_A = {n: len(self.get_real_neighbors(self.G_A, n)) for n in nodes_A}
        degree_B = {n: len(self.get_real_neighbors(self.G_B, n)) for n in nodes_B}
        
        candidates = {}
        for nodeA in nodes_A:
            candidates[nodeA] = [
                nodeB for nodeB in nodes_B
                if (self.G_A.nodes[nodeA]['type'] == self.G_B.nodes[nodeB]['type'] and
                    degree_A[nodeA] == degree_B[nodeB])
            ]
        
        return candidates
    
    def validate_edge_constraints(self, mapping: Dict[int, int]) -> bool:
        """Validazione rigorosa delle connessioni tra nodi mappati."""
        # 1. Controllo struttura delle connessioni
        for nodeA, nodeB in mapping.items():
            neighborsA = self.get_real_neighbors(self.G_A, nodeA)
            neighborsB = self.get_real_neighbors(self.G_B, nodeB)
            
            # Conteggio delle connessioni mappate
            mapped_connections_A = [n for n in neighborsA if n in mapping]
            mapped_connections_B = [mapping[n] for n in mapped_connections_A]
            
            # Verifica che tutte le connessioni mappate esistano in B
            for connB in mapped_connections_B:
                if connB not in neighborsB:
                    return False
            
            # Verifica reciprocità delle connessioni
            for neighbor_mapped in mapped_connections_B:
                # Il nodo mappato deve avere nodeB tra i suoi vicini
                neighbors_of_mapped = self.get_real_neighbors(self.G_B, neighbor_mapped)
                if nodeB not in neighbors_of_mapped:
                    return False
        
        # 2. Controllo coerenza dei pattern di connessione
        for nodeA1, nodeB1 in mapping.items():
            for nodeA2, nodeB2 in mapping.items():
                if nodeA1 >= nodeA2:  # Evita duplicati
                    continue
                    
                patternA = self.get_connection_pattern(self.G_A, nodeA1, nodeA2)
                patternB = self.get_connection_pattern(self.G_B, nodeB1, nodeB2)
                
                # Regole di compatibilità più rigorose
                if patternA == "none" and patternB != "none":
                    return False
                if patternA != "none" and patternB == "none":
                    return False
                if patternA == "edge_added" and patternB != "edge_added":
                    return False
                if patternA in ("direct", "via_node") and patternB not in ("direct", "via_node"):
                    return False
        
        return True
    
    def validate_geometric_constraints(self, mapping: Dict[int, int]) -> bool:
        """Validazione rigorosa dei vincoli geometrici."""
        node2idx_A = self.G_A.graph['_node2idx']
        node2idx_B = self.G_B.graph['_node2idx']
        
        for nodeA1, nodeB1 in mapping.items():
            for nodeA2, nodeB2 in mapping.items():
                if nodeA1 >= nodeA2:
                    continue
                
                # 1. Controllo rapporti lunghezze archi
                try:
                    idx_A1, idx_A2 = node2idx_A[nodeA1], node2idx_A[nodeA2]
                    idx_B1, idx_B2 = node2idx_B[nodeB1], node2idx_B[nodeB2]
                    
                    dist_A = self.M3_A[idx_A1][idx_A2]
                    dist_B = self.M3_B[idx_B1][idx_B2]
                    
                    if dist_A != float('inf') and dist_B != float('inf') and dist_A > 0 and dist_B > 0:
                        ratio = max(dist_A, dist_B) / min(dist_A, dist_B)
                        if ratio > self.max_edge_length_ratio:
                            return False
                except (IndexError, KeyError):
                    continue
                
                # 2. Controllo scavalcamenti
                try:
                    scav_A = self.M_scav_A[nodeA1][nodeA2]
                    scav_B = self.M_scav_B[nodeB1][nodeB2]
                    if abs(scav_A - scav_B) > self.max_ridge_diff:
                        return False
                except (IndexError, KeyError):
                    continue
                
                # 3. Controllo angoli
                try:
                    angleA = self.get_angle_along_path(self.G_A, nodeA1, nodeA2)
                    angleB = self.get_angle_along_path(self.G_B, nodeB1, nodeB2)
                    
                    if angleA is not None and angleB is not None:
                        angle_diff = min(abs(angleA - angleB), 360.0 - abs(angleA - angleB))
                        if angle_diff > self.angle_tolerance:
                            return False
                except (KeyError, TypeError):
                    continue
        
        return True
    
    def validate_chirality(self, mapping: Dict[int, int]) -> bool:
        """Controllo chiralità ottimizzato con verifica efficiente delle terne di nodi."""
        def orientation(p1, p2, p3):
            """Calcola orientazione usando prodotto vettoriale (cross product)."""
            return (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])
        
        def distance_squared(p1, p2):
            """Calcola distanza al quadrato per evitare sqrt."""
            return (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2
        
        # Cache per posizioni dei nodi per evitare accessi ripetuti
        pos_cache_A = {}
        pos_cache_B = {}
        for nodeA, nodeB in mapping.items():
            try:
                pos_cache_A[nodeA] = self.G_A.nodes[nodeA]['pos']
                pos_cache_B[nodeB] = self.G_B.nodes[nodeB]['pos']
            except KeyError:
                continue
        
        total_triplets = 0
        consistent_triplets = 0
        tested_triplets = set()  # Evita duplicati
        
        # Strategia 1: Test terne con nodo centrale
        for nodeA, nodeB in mapping.items():
            if nodeA not in pos_cache_A or nodeB not in pos_cache_B:
                continue
                
            neighborsA = self.get_real_neighbors(self.G_A, nodeA)
            mapped_neighbors = [n for n in neighborsA if n in mapping and n in pos_cache_A]
            
            if len(mapped_neighbors) < 2:
                continue
            
            # Test tutte le combinazioni di vicini
            for i in range(len(mapped_neighbors)):
                for j in range(i + 1, len(mapped_neighbors)):
                    n1A, n2A = mapped_neighbors[i], mapped_neighbors[j]
                    n1B, n2B = mapping[n1A], mapping[n2A]
                    
                    if n1B not in pos_cache_B or n2B not in pos_cache_B:
                        continue
                    
                    # Evita test duplicati ordinando la terna
                    triplet_key = tuple(sorted([nodeA, n1A, n2A]))
                    if triplet_key in tested_triplets:
                        continue
                    tested_triplets.add(triplet_key)
                    
                    # Calcola orientazioni
                    orient_A = orientation(pos_cache_A[nodeA], pos_cache_A[n1A], pos_cache_A[n2A])
                    orient_B = orientation(pos_cache_B[nodeB], pos_cache_B[n1B], pos_cache_B[n2B])
                    
                    # Filtro casi degeneri con soglia più robusta
                    if abs(orient_A) < 1e-6 or abs(orient_B) < 1e-6:
                        continue
                    
                    total_triplets += 1
                    if (orient_A > 0) == (orient_B > 0):  # Coerenza chirali
                        consistent_triplets += 1
        
        # Strategia 2: Test terne non centralizzate per maggiore copertura
        mapped_nodes = list(mapping.keys())
        for i in range(len(mapped_nodes)):
            for j in range(i + 1, len(mapped_nodes)):
                for k in range(j + 1, len(mapped_nodes)):
                    nodeA1, nodeA2, nodeA3 = mapped_nodes[i], mapped_nodes[j], mapped_nodes[k]
                    nodeB1, nodeB2, nodeB3 = mapping[nodeA1], mapping[nodeA2], mapping[nodeA3]
                    
                    # Controlla se tutti i nodi hanno posizioni valide
                    if not all(n in pos_cache_A for n in [nodeA1, nodeA2, nodeA3]):
                        continue
                    if not all(n in pos_cache_B for n in [nodeB1, nodeB2, nodeB3]):
                        continue
                    
                    # Evita test duplicati
                    triplet_key = tuple(sorted([nodeA1, nodeA2, nodeA3]))
                    if triplet_key in tested_triplets:
                        continue
                    tested_triplets.add(triplet_key)
                    
                    # Filtra terne troppo piccole (potrebbero essere imprecise)
                    min_dist_A = min(distance_squared(pos_cache_A[nodeA1], pos_cache_A[nodeA2]),
                                   distance_squared(pos_cache_A[nodeA2], pos_cache_A[nodeA3]),
                                   distance_squared(pos_cache_A[nodeA3], pos_cache_A[nodeA1]))
                    if min_dist_A < 100:  # Soglia minima per evitare rumore
                        continue
                    
                    # Test tutte e 3 le orientazioni possibili per robustezza
                    orientations_A = [
                        orientation(pos_cache_A[nodeA1], pos_cache_A[nodeA2], pos_cache_A[nodeA3]),
                        orientation(pos_cache_A[nodeA2], pos_cache_A[nodeA3], pos_cache_A[nodeA1]),
                        orientation(pos_cache_A[nodeA3], pos_cache_A[nodeA1], pos_cache_A[nodeA2])
                    ]
                    orientations_B = [
                        orientation(pos_cache_B[nodeB1], pos_cache_B[nodeB2], pos_cache_B[nodeB3]),
                        orientation(pos_cache_B[nodeB2], pos_cache_B[nodeB3], pos_cache_B[nodeB1]),
                        orientation(pos_cache_B[nodeB3], pos_cache_B[nodeB1], pos_cache_B[nodeB2])
                    ]
                    
                    valid_orientations = 0
                    consistent_orientations = 0
                    
                    for orient_A, orient_B in zip(orientations_A, orientations_B):
                        if abs(orient_A) < 1e-6 or abs(orient_B) < 1e-6:
                            continue
                        valid_orientations += 1
                        if (orient_A > 0) == (orient_B > 0):
                            consistent_orientations += 1
                    
                    if valid_orientations > 0:
                        total_triplets += 1
                        # Richiede che almeno 2/3 delle orientazioni siano consistenti
                        if consistent_orientations >= max(1, valid_orientations * 2 // 3):
                            consistent_triplets += 1
        
        if total_triplets == 0:
            return True  # Nessuna terna testabile, accetta mapping
        
        # Soglia configurabile o dinamica basata sul numero di nodi
        if self.chirality_threshold is not None:
            threshold = self.chirality_threshold
        else:
            num_nodes = len(mapping)
            if num_nodes <= 3:
                threshold = 0.75  # Più permissivo per pochi nodi
            elif num_nodes <= 5:
                threshold = 0.80  # Gradualmente più rigoroso
            else:
                threshold = 0.85  # Standard per molti nodi
        
        consistency_ratio = consistent_triplets / total_triplets
        return consistency_ratio >= threshold
    
    def partial_validation(self, mapping: Dict[int, int], nodeA: int, nodeB: int) -> bool:
        """Validazione rapida durante il backtracking."""
        # Controllo solo le connessioni già mappate
        for nA_mapped in mapping:
            if nA_mapped == nodeA:
                continue
            
            nB_mapped = mapping[nA_mapped]
            
            # Verifica esistenza connessione
            neighborsA = self.get_real_neighbors(self.G_A, nodeA)
            neighborsB = self.get_real_neighbors(self.G_B, nodeB)
            
            if (nA_mapped in neighborsA) != (nB_mapped in neighborsB):
                return False
            
            # Se sono connessi, verifica pattern e angolo
            if nA_mapped in neighborsA:
                patternA = self.get_connection_pattern(self.G_A, nodeA, nA_mapped)
                patternB = self.get_connection_pattern(self.G_B, nodeB, nB_mapped)
                
                # Controllo pattern
                if patternA == "edge_added" and patternB != "edge_added":
                    return False
                if patternA in ("direct", "via_node") and patternB not in ("direct", "via_node"):
                    return False
                
                # Controllo angolo
                angleA = self.get_angle_along_path(self.G_A, nodeA, nA_mapped)
                angleB = self.get_angle_along_path(self.G_B, nodeB, nB_mapped)
                
                if angleA is not None and angleB is not None:
                    angle_diff = min(abs(angleA - angleB), 360.0 - abs(angleA - angleB))
                    if angle_diff > self.angle_tolerance:
                        return False
        
        return True
    
    def fast_discard_check(self, nodes_A: List[int], nodes_B: List[int]) -> bool:
        """Fast discard pre-checks per efficienza."""
        if len(nodes_A) != len(nodes_B):
            return False
        
        # Controllo rapido sequence gradi
        degrees_A = sorted([len(self.get_real_neighbors(self.G_A, n)) for n in nodes_A])
        degrees_B = sorted([len(self.get_real_neighbors(self.G_B, n)) for n in nodes_B])
        if degrees_A != degrees_B:
            return False
        
        # Controllo rapido numero archi totali
        edges_A = sum(1 for i, nodeA in enumerate(nodes_A) 
                     for j in range(i+1, len(nodes_A)) 
                     if nodes_A[j] in self.get_real_neighbors(self.G_A, nodeA))
        edges_B = sum(1 for i, nodeB in enumerate(nodes_B) 
                     for j in range(i+1, len(nodes_B)) 
                     if nodes_B[j] in self.get_real_neighbors(self.G_B, nodeB))
        if edges_A != edges_B:
            return False
            
        return True

    def vf2_match(self, nodes_A: List[int], nodes_B: List[int]) -> Optional[Dict[int, int]]:
        """Implementazione dell'algoritmo VF2 per isomorfismo di sottografi."""
        # Fast discard pre-check
        if not self.fast_discard_check(nodes_A, nodes_B):
            return None
            
        # Stati del matching VF2
        core_A = {}  # Mapping A -> B
        core_B = {}  # Mapping B -> A
        in_A = set()   # Nodi A nel terminal set
        in_B = set()   # Nodi B nel terminal set
        out_A = set()  # Nodi A non ancora considerati
        out_B = set()  # Nodi B non ancora considerati
        
        # Inizializza out sets
        out_A.update(nodes_A)
        out_B.update(nodes_B)
        
        def update_terminal_sets(nodeA: int, nodeB: int):
            """Aggiorna i terminal sets dopo aver aggiunto una coppia al core."""
            # Aggiorna in_A
            for neighbor in self.get_real_neighbors(self.G_A, nodeA):
                if neighbor in nodes_A and neighbor not in core_A:
                    in_A.add(neighbor)
                    out_A.discard(neighbor)
            
            # Aggiorna in_B  
            for neighbor in self.get_real_neighbors(self.G_B, nodeB):
                if neighbor in nodes_B and neighbor not in core_B:
                    in_B.add(neighbor)
                    out_B.discard(neighbor)
        
        def feasibility_check(nodeA: int, nodeB: int) -> bool:
            """Controllo di fattibilità VF2."""
            # 1. Controllo compatibilità nodi
            if (self.G_A.nodes[nodeA]['type'] != self.G_B.nodes[nodeB]['type']):
                return False
            
            # 2. Controllo connessioni nel core
            for coreA, coreB in core_A.items():
                # Se nodeA è connesso a coreA, allora nodeB deve essere connesso a coreB
                connectedA = coreA in self.get_real_neighbors(self.G_A, nodeA)
                connectedB = coreB in self.get_real_neighbors(self.G_B, nodeB)
                if connectedA != connectedB:
                    return False
            
            # 3. Controlli di cardinalità VF2
            # Terminal sets
            pred_A = len([n for n in self.get_real_neighbors(self.G_A, nodeA) 
                         if n in in_A and n not in core_A])
            pred_B = len([n for n in self.get_real_neighbors(self.G_B, nodeB) 
                         if n in in_B and n not in core_B])
            if pred_A != pred_B:
                return False
                
            succ_A = len([n for n in self.get_real_neighbors(self.G_A, nodeA) 
                         if n in out_A])
            succ_B = len([n for n in self.get_real_neighbors(self.G_B, nodeB) 
                         if n in out_B])
            if succ_A != succ_B:
                return False
            
            return True
        
        def semantic_check(nodeA: int, nodeB: int) -> bool:
            """Controlli semantici bilanciati per VF2."""
            for coreA, coreB in core_A.items():
                # Verifica se esiste connessione
                connectedA = coreA in self.get_real_neighbors(self.G_A, nodeA)
                connectedB = coreB in self.get_real_neighbors(self.G_B, nodeB)
                
                # Controllo connessione strict
                if connectedA != connectedB:
                    return False
                
                # Se sono connessi, controlli specifici
                if connectedA:
                    # 1. Pattern di connessione - STRICT al 100%
                    patternA = self.get_connection_pattern(self.G_A, nodeA, coreA)
                    patternB = self.get_connection_pattern(self.G_B, nodeB, coreB)
                    
                    # Pattern deve essere identico al 100%
                    if patternA != patternB:
                        return False
                    
                    # 2. Controllo angolazione - ridotto del 20%
                    angleA = self.get_angle_along_path(self.G_A, nodeA, coreA)
                    angleB = self.get_angle_along_path(self.G_B, nodeB, coreB)
                    
                    if angleA is not None and angleB is not None:
                        angle_diff = min(abs(angleA - angleB), 360.0 - abs(angleA - angleB))
                        # Tolleranza ridotta del 20%: da 1.5x a 1.2x
                        if angle_diff > self.angle_tolerance * 1.2:
                            return False
                    
                    # 3. Controllo lunghezza percorso - mantenuto 1.5x
                    if (self.M3_A is not None and len(self.M3_A) > 0 and 
                        self.M3_B is not None and len(self.M3_B) > 0):
                        try:
                            node2idx_A = self.G_A.graph['_node2idx']
                            node2idx_B = self.G_B.graph['_node2idx']
                            
                            idx_A1, idx_A2 = node2idx_A[nodeA], node2idx_A[coreA]
                            idx_B1, idx_B2 = node2idx_B[nodeB], node2idx_B[coreB]
                            
                            dist_A = self.M3_A[idx_A1][idx_A2]
                            dist_B = self.M3_B[idx_B1][idx_B2]
                            
                            if (dist_A != float('inf') and dist_B != float('inf') and 
                                dist_A > 0 and dist_B > 0):
                                ratio = max(dist_A, dist_B) / min(dist_A, dist_B)
                                if ratio > self.max_edge_length_ratio * 1.5:  # Mantenuto 1.5x
                                    return False
                        except (IndexError, KeyError):
                            pass  # Ignora errori di calcolo
            
            return True
        
        def get_candidate_pairs():
            """Genera coppie candidate secondo le regole VF2 con ordinamento efficiente."""
            # Prima priorità: terminal sets non vuoti
            if in_A and in_B:
                # Seleziona nodo con meno candidati possibili (MRV)
                nodeA = min(in_A, key=lambda n: len([b for b in in_B 
                                                   if self.G_A.nodes[n]['type'] == self.G_B.nodes[b]['type']]))
                # Ordina candidati per grado (nodi con più connessioni prima)
                candidates = sorted([b for b in in_B 
                                   if self.G_A.nodes[nodeA]['type'] == self.G_B.nodes[b]['type']],
                                  key=lambda n: len(self.get_real_neighbors(self.G_B, n)), reverse=True)
                for nodeB in candidates:
                    yield nodeA, nodeB
            # Seconda priorità: out sets
            elif out_A and out_B:
                # Seleziona nodo con meno candidati possibili (MRV)
                nodeA = min(out_A, key=lambda n: len([b for b in out_B 
                                                    if self.G_A.nodes[n]['type'] == self.G_B.nodes[b]['type']]))
                # Ordina candidati per grado
                candidates = sorted([b for b in out_B 
                                   if self.G_A.nodes[nodeA]['type'] == self.G_B.nodes[b]['type']],
                                  key=lambda n: len(self.get_real_neighbors(self.G_B, n)), reverse=True)
                for nodeB in candidates:
                    yield nodeA, nodeB
        
        # Contatore per limitare iterazioni
        max_iterations = len(nodes_A) * len(nodes_B) * 10  # Limite ragionevole
        iteration_count = [0]
        
        def vf2_recursive() -> bool:
            """Ricorsione VF2 con limite di iterazioni e controllo chiralità."""
            iteration_count[0] += 1
            if iteration_count[0] > max_iterations:
                return False  # Timeout per efficienza
            
            if len(core_A) == len(nodes_A):
                # Controllo chiralità finale per validazione completa
                return self.validate_chirality(core_A)
            
            # Controllo chiralità intermedio se abbiamo almeno 3 nodi mappati
            if len(core_A) >= 3 and len(core_A) % 2 == 0:  # Ogni 2 nodi mappati
                if not self.validate_chirality(core_A):
                    return False  # Early termination per inconsistenza chirali
            
            # Early termination se troppi controlli falliti
            candidate_count = 0
            failed_count = 0
            
            for nodeA, nodeB in get_candidate_pairs():
                candidate_count += 1
                if not feasibility_check(nodeA, nodeB):
                    failed_count += 1
                    continue
                    
                if not semantic_check(nodeA, nodeB):
                    failed_count += 1
                    continue
                
                # Salva stato corrente
                old_in_A = in_A.copy()
                old_in_B = in_B.copy()
                old_out_A = out_A.copy()
                old_out_B = out_B.copy()
                
                # Aggiungi al core
                core_A[nodeA] = nodeB
                core_B[nodeB] = nodeA
                
                # Rimuovi dai set correnti
                in_A.discard(nodeA)
                in_B.discard(nodeB)
                out_A.discard(nodeA)
                out_B.discard(nodeB)
                
                # Aggiorna terminal sets
                update_terminal_sets(nodeA, nodeB)
                
                # Ricorsione
                if vf2_recursive():
                    return True
                
                # Backtrack
                del core_A[nodeA]
                del core_B[nodeB]
                
                # Ripristina stati
                in_A.clear()
                in_A.update(old_in_A)
                in_B.clear()
                in_B.update(old_in_B)
                out_A.clear()
                out_A.update(old_out_A)
                out_B.clear()
                out_B.update(old_out_B)
                
                # Early termination se troppi fallimenti
                if candidate_count >= 5 and failed_count / candidate_count > 0.8:
                    break  # Troppi fallimenti, abbandona
            
            return False
        
        # Avvia VF2
        if vf2_recursive():
            return core_A.copy()
        return None

    def find_mapping(self, nodes_A: List[int], nodes_B: List[int]) -> Optional[Dict[int, int]]:
        """Trova mapping usando VF2 algorithm."""
        if not self.check_structural_compatibility(nodes_A, nodes_B):
            return None
        
        return self.vf2_match(nodes_A, nodes_B)
    
    def compute_mapping_score(self, mapping: Dict[int, int]) -> float:
        """Calcola score complessivo del mapping."""
        if not mapping:
            return 0.0
        
        node2idx_A = self.G_A.graph['_node2idx']
        node2idx_B = self.G_B.graph['_node2idx']
        
        total_score = 0.0
        total_pairs = 0
        
        nodes = list(mapping.keys())
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                nodeA1, nodeA2 = nodes[i], nodes[j]
                nodeB1, nodeB2 = mapping[nodeA1], mapping[nodeA2]
                
                # Score distanza
                try:
                    idx_A1, idx_A2 = node2idx_A[nodeA1], node2idx_A[nodeA2]
                    idx_B1, idx_B2 = node2idx_B[nodeB1], node2idx_B[nodeB2]
                    
                    dist_A = self.M3_A[idx_A1][idx_A2]
                    dist_B = self.M3_B[idx_B1][idx_B2]
                    
                    if dist_A != float('inf') and dist_B != float('inf') and dist_A > 0 and dist_B > 0:
                        ratio = min(dist_A, dist_B) / max(dist_A, dist_B)
                        distance_score = ratio
                    else:
                        distance_score = 0.5
                except (IndexError, KeyError):
                    distance_score = 0.5
                
                # Score angolo
                try:
                    angleA = self.get_angle_along_path(self.G_A, nodeA1, nodeA2)
                    angleB = self.get_angle_along_path(self.G_B, nodeB1, nodeB2)
                    
                    if angleA is not None and angleB is not None:
                        angle_diff = min(abs(angleA - angleB), 360.0 - abs(angleA - angleB))
                        angle_score = max(0.0, 1.0 - angle_diff / 180.0)
                    else:
                        angle_score = 0.5
                except (KeyError, TypeError):
                    angle_score = 0.5
                
                # Score pattern connessione
                patternA = self.get_connection_pattern(self.G_A, nodeA1, nodeA2)
                patternB = self.get_connection_pattern(self.G_B, nodeB1, nodeB2)
                pattern_score = 1.0 if patternA == patternB else 0.3
                
                # Score complessivo della coppia (pesato)
                pair_score = 0.4 * distance_score + 0.4 * angle_score + 0.2 * pattern_score
                total_score += pair_score
                total_pairs += 1
        
        return total_score / total_pairs if total_pairs > 0 else 0.0


def match_subgraph(G_A: nx.Graph, G_B: nx.Graph, M3_A=None, M3_B=None, M_scav_A=None, M_scav_B=None, 
                   angle_tolerance_degrees=30, max_edge_length_ratio=3.0, chirality_threshold=None, **kwargs):
    """Interfaccia principale per il matching tra sottografi usando VF2 raffinato."""
    
    # Crea matcher con parametri geometrici e controllo chiralità
    matcher = GraphMatcher(
        G_A, G_B, 
        M3_A if M3_A is not None else [], 
        M3_B if M3_B is not None else [], 
        M_scav_A if M_scav_A is not None else [], 
        M_scav_B if M_scav_B is not None else [],
        angle_tolerance=angle_tolerance_degrees, max_ridge_diff=1, 
        max_edge_length_ratio=max_edge_length_ratio,
        chirality_threshold=chirality_threshold
    )
    
    real_nodes_A = matcher.get_real_nodes(G_A)
    real_nodes_B = matcher.get_real_nodes(G_B)
    
    # Usa VF2 per trovare isomorfismo
    mapping = matcher.vf2_match(real_nodes_A, real_nodes_B)
    if mapping is None:
        return False, {}, 0.0, {"reason": "no_isomorphism", "algorithm": "VF2"}
    
    # Controllo chiralità ottimizzato con terne di nodi
    if not matcher.validate_chirality(mapping):
        return False, {}, 0.0, {"reason": "chirality_mismatch", "algorithm": "VF2+Chirality"}
    
    # Score basato sulla validazione chirali e sul numero di nodi mappati
    score = 1.0 if mapping else 0.0
    
    return True, mapping, score, {"validation": "passed", "nodes_mapped": len(mapping), "algorithm": "VF2"}


# Funzioni di compatibilità con il codice esistente
def is_real_node(G, node):
    return G.nodes[node].get('type') != 'added'

def get_real_nodes(G):
    return [node for node in G.nodes() if is_real_node(G, node)]

def check_node_compatibility(G_A, G_B, nodeA, nodeB):
    return (is_real_node(G_A, nodeA) and is_real_node(G_B, nodeB) and
            G_A.nodes[nodeA].get('type') == G_B.nodes[nodeB].get('type'))