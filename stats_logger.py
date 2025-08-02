# stats_logger.py
import csv, json, os, threading, time
from datetime import datetime

class StatsLogger:
    """Thread-safe CSV+JSON logger per i match."""
    def __init__(self, out_dir: str, csv_filename="scores.csv"):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.dir = os.path.join(out_dir, f"run_{ts}")
        os.makedirs(self.dir, exist_ok=True)

        self.csv_path = os.path.join(self.dir, csv_filename)
        self.json_path = os.path.join(self.dir, "details.ndjson")
        self._lock = threading.Lock()

        # header CSV: un record per *coppia di impronte* (non per singolo sotto-sottografo)
        with open(self.csv_path, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["idA", "idB", "relation",          # pair metadata
                        "subgraph_id", "nodes_mapped",     # granularità sub-subgraph
                        "score"])                          # score complessivo

    def log(self, *, idA, idB, relation, subgraph_id,
            nodes_mapped, score, pair_details=None):
        """Scrive una riga CSV + opzionale JSON riga-per-riga."""
        with self._lock:
            with open(self.csv_path, "a", newline="") as fh:
                csv.writer(fh).writerow(
                    [idA, idB, relation, subgraph_id, nodes_mapped, score])

            if pair_details is not None:
                with open(self.json_path, "a") as jh:
                    jh.write(json.dumps({
                        "idA": idA, "idB": idB,
                        "subgraph_id": subgraph_id,
                        "score": score,
                        "details": pair_details
                    }) + "\n")
