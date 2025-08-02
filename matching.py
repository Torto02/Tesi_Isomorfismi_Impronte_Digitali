
import networkx as nx
import math
from collections import deque
from typing import Dict, List, Tuple, Set, Optional


class GraphMatcher:
    """Classe unificata per il matching tra sottografi con controlli rigorosi."""
    
    def __init__(self, G_A: nx.Graph, G_B: nx.Graph, M3_A, M3_B, 
                 M_scav_A, M_scav_B, angle_tolerance: float = 30.0,
                 max_ridge_diff: int = 1, max_edge_length_ratio: float = 3.0):
        self.G_A = G_A
        self.G_B = G_B
        self.M3_A = M3_A
        self.M3_B = M3_B
        self.M_scav_A = M_scav_A
        self.M_scav_B = M_scav_B
        self.angle_tolerance = angle_tolerance
        self.max_ridge_diff = max_ridge_diff
        self.max_edge_length_ratio = max_edge_length_ratio
        
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
        """Controllo chiralità migliorato con soglia di tolleranza."""
        def orientation(p1, p2, p3):
            return (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])
        
        total_triplets = 0
        consistent_triplets = 0
        
        for nodeA, nodeB in mapping.items():
            neighborsA = self.get_real_neighbors(self.G_A, nodeA)
            mapped_neighbors = [n for n in neighborsA if n in mapping]
            
            if len(mapped_neighbors) < 2:
                continue
            
            # Test tutte le triplette con nodeA al centro
            for i in range(len(mapped_neighbors)):
                for j in range(i + 1, len(mapped_neighbors)):
                    n1A, n2A = mapped_neighbors[i], mapped_neighbors[j]
                    n1B, n2B = mapping[n1A], mapping[n2A]
                    
                    try:
                        posA = self.G_A.nodes[nodeA]['pos']
                        pos1A = self.G_A.nodes[n1A]['pos']
                        pos2A = self.G_A.nodes[n2A]['pos']
                        
                        posB = self.G_B.nodes[nodeB]['pos']
                        pos1B = self.G_B.nodes[n1B]['pos']
                        pos2B = self.G_B.nodes[n2B]['pos']
                        
                        orient_A = orientation(posA, pos1A, pos2A)
                        orient_B = orientation(posB, pos1B, pos2B)
                        
                        # Ignora casi degeneri
                        if abs(orient_A) < 1e-9 or abs(orient_B) < 1e-9:
                            continue
                        
                        total_triplets += 1
                        if (orient_A > 0) == (orient_B > 0):  # Stesso segno
                            consistent_triplets += 1
                            
                    except KeyError:
                        continue
        
        if total_triplets == 0:
            return True
        
        # Richiede almeno 85% di coerenza chirali
        consistency_ratio = consistent_triplets / total_triplets
        return consistency_ratio >= 0.85
    
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
    
    def find_mapping(self, nodes_A: List[int], nodes_B: List[int]) -> Optional[Dict[int, int]]:
        """Trova mapping ottimale usando backtracking migliorato."""
        if not self.check_structural_compatibility(nodes_A, nodes_B):
            return None
        
        candidates = self.build_candidate_map(nodes_A, nodes_B)
        if any(len(cands) == 0 for cands in candidates.values()):
            return None
        
        # Ordina nodi per MRV (Most Restricted Variable)
        ordered_nodes = sorted(nodes_A, key=lambda n: len(candidates[n]))
        
        def backtrack(index: int, mapping: Dict[int, int], used_B: Set[int]) -> Optional[Dict[int, int]]:
            if index == len(ordered_nodes):
                return mapping.copy()
            
            nodeA = ordered_nodes[index]
            for nodeB in candidates[nodeA]:
                if nodeB in used_B:
                    continue
                
                # Validazione rapida
                if not self.partial_validation(mapping, nodeA, nodeB):
                    continue
                
                # Aggiorna mapping e continua
                mapping[nodeA] = nodeB
                used_B.add(nodeB)
                
                result = backtrack(index + 1, mapping, used_B)
                if result is not None:
                    return result
                
                # Backtrack
                del mapping[nodeA]
                used_B.remove(nodeB)
            
            return None
        
        return backtrack(0, {}, set())
    
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


def match_subgraph(G_A: nx.Graph, G_B: nx.Graph, M3_A, M3_B, M_scav_A, M_scav_B, 
                  cost_threshold_rel: float = 0.5, max_ridge_diff: int = 1, 
                  angle_tolerance_degrees: float = 30, max_edge_length_ratio: float = 3.0):
    """Interfaccia principale per il matching tra sottografi."""
    
    matcher = GraphMatcher(
        G_A, G_B, M3_A, M3_B, M_scav_A, M_scav_B,
        angle_tolerance=angle_tolerance_degrees,
        max_ridge_diff=max_ridge_diff,
        max_edge_length_ratio=max_edge_length_ratio
    )
    
    real_nodes_A = matcher.get_real_nodes(G_A)
    real_nodes_B = matcher.get_real_nodes(G_B)
    
    # Trova mapping
    mapping = matcher.find_mapping(real_nodes_A, real_nodes_B)
    if mapping is None:
        return False, {}, 0.0, {}
    
    # Validazioni finali rigorose
    if not matcher.validate_edge_constraints(mapping):
        return False, {}, 0.0, {}
    
    if not matcher.validate_geometric_constraints(mapping):
        return False, {}, 0.0, {}
    
    if not matcher.validate_chirality(mapping):
        return False, {}, 0.0, {}
    
    # Calcola score finale
    score = matcher.compute_mapping_score(mapping)
    
    return True, mapping, score, {"validation": "passed", "nodes_mapped": len(mapping)}


# Funzioni di compatibilità con il codice esistente
def is_real_node(G, node):
    return G.nodes[node].get('type') != 'added'

def get_real_nodes(G):
    return [node for node in G.nodes() if is_real_node(G, node)]

def check_node_compatibility(G_A, G_B, nodeA, nodeB):
    return (is_real_node(G_A, nodeA) and is_real_node(G_B, nodeB) and
            G_A.nodes[nodeA].get('type') == G_B.nodes[nodeB].get('type'))