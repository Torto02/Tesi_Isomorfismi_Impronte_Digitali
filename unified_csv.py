#!/usr/bin/env python3
"""
Script per aggregare i file CSV di confronto.
1) Crea un CSV unificato con tutti i dati
2) Crea un CSV per ogni impronta con tutti i suoi confronti
"""

import os
import pandas as pd
from pathlib import Path
from collections import defaultdict

class CSVAggregator:
    def __init__(self, base_dir="All_comparisons", output_dir="Aggregated_Results"):
        self.base_dir = Path(base_dir)
        self.output_dir = Path(output_dir)
        self.all_data = []
        self.fingerprint_data = defaultdict(list)
        self.files_processed = 0
        self.total_rows = 0
        
    def setup_output_directory(self):
        """Crea la directory di output se non esiste."""
        self.output_dir.mkdir(exist_ok=True)
        
        # Crea sottocartelle
        (self.output_dir / "by_fingerprint").mkdir(exist_ok=True)
        
    def process_csv_file(self, csv_file_path):
        """
        Processa un singolo file CSV.
        
        Args:
            csv_file_path: Path al file CSV
            
        Returns:
            DataFrame del file processato
        """
        try:
            df = pd.read_csv(csv_file_path)
            
            if df.empty:
                print(f"  File vuoto: {csv_file_path.name}")
                return df
                
            # Aggiungi informazioni sul file sorgente
            df['source_file'] = csv_file_path.name
            df['source_folder'] = csv_file_path.parent.name
            
            print(f"  Processato: {csv_file_path.name} ({len(df)} righe)")
            return df
            
        except Exception as e:
            print(f"  Errore nel processare {csv_file_path}: {e}")
            return pd.DataFrame()
    
    def aggregate_by_fingerprint(self, df):
        """
        Raggruppa i dati per impronta.
        
        Args:
            df: DataFrame con i dati del CSV
        """
        for _, row in df.iterrows():
            idA = str(row.get('idA', ''))
            idB = str(row.get('idB', ''))
            
            # Aggiungi la riga ai dati dell'impronta A
            if idA and idA != 'nan':
                self.fingerprint_data[idA].append(row.to_dict())
                
            # Aggiungi la riga ai dati dell'impronta B
            if idB and idB != 'nan' and idB != idA:
                self.fingerprint_data[idB].append(row.to_dict())
    
    def scan_all_csv_files(self):
        """Scansiona tutti i file CSV e aggrega i dati."""
        if not self.base_dir.exists():
            print(f"Errore: Directory {self.base_dir} non trovata!")
            return False
            
        print(f"Scansionando directory: {self.base_dir.absolute()}")
        
        # Trova tutti i file CSV nelle sottocartelle
        csv_files = list(self.base_dir.rglob("*.csv"))
        
        if not csv_files:
            print("Nessun file CSV trovato!")
            return False
            
        print(f"Trovati {len(csv_files)} file CSV da processare\n")
        
        # Processa ogni file CSV
        for csv_file in csv_files:
            print(f"Processando: {csv_file.relative_to(self.base_dir)}")
            self.files_processed += 1
            
            df = self.process_csv_file(csv_file)
            
            if not df.empty:
                # Aggiungi ai dati totali
                self.all_data.append(df)
                self.total_rows += len(df)
                
                # Aggrega per impronta
                self.aggregate_by_fingerprint(df)
            
            print()  # Riga vuota per separare
            
        return True
    
    def create_unified_csv(self):
        """Crea il CSV unificato con tutti i dati."""
        if not self.all_data:
            print("Nessun dato da unificare.")
            return
            
        print("Creando CSV unificato...")
        
        # Concatena tutti i DataFrame
        unified_df = pd.concat(self.all_data, ignore_index=True)
        
        # Ordina per idA, idB
        unified_df = unified_df.sort_values(['idA', 'idB'], na_position='last')
        
        # Salva il file unificato
        output_file = self.output_dir / "all_comparisons_unified.csv"
        unified_df.to_csv(output_file, index=False)
        
        print(f"✅ CSV unificato salvato: {output_file}")
        print(f"   Totale righe: {len(unified_df)}")
        print(f"   Colonne: {list(unified_df.columns)}")
        
        return unified_df
    
    def create_fingerprint_csvs(self):
        """Crea un CSV per ogni impronta."""
        if not self.fingerprint_data:
            print("Nessun dato per impronte individuali.")
            return
            
        print(f"\nCreando CSV individuali per {len(self.fingerprint_data)} impronte...")
        
        fingerprint_output_dir = self.output_dir / "by_fingerprint"
        
        for fingerprint_id, rows in self.fingerprint_data.items():
            try:
                # Crea DataFrame per questa impronta
                fp_df = pd.DataFrame(rows)
                
                # Ordina per idA, idB
                fp_df = fp_df.sort_values(['idA', 'idB'], na_position='last')
                
                # Nome file sicuro (rimuovi caratteri non validi)
                safe_filename = "".join(c for c in fingerprint_id if c.isalnum() or c in ('-', '_', '.')).rstrip()
                output_file = fingerprint_output_dir / f"{safe_filename}_comparisons.csv"
                
                # Salva il file
                fp_df.to_csv(output_file, index=False)
                
                print(f"  ✅ {fingerprint_id}: {len(fp_df)} confronti → {output_file.name}")
                
            except Exception as e:
                print(f"  ❌ Errore per {fingerprint_id}: {e}")
    
    def create_summary_report(self):
        """Crea un report riassuntivo."""
        print("\nCreando report riassuntivo...")
        
        # Statistiche generali
        summary_data = {
            'total_files_processed': [self.files_processed],
            'total_rows': [self.total_rows],
            'unique_fingerprints': [len(self.fingerprint_data)],
            'avg_comparisons_per_fingerprint': [self.total_rows / len(self.fingerprint_data) if self.fingerprint_data else 0]
        }
        
        # Statistiche per impronta
        fingerprint_stats = []
        for fp_id, rows in self.fingerprint_data.items():
            df = pd.DataFrame(rows)
            
            # Conta relazioni
            relation_counts = df['relation'].value_counts().to_dict() if 'relation' in df.columns else {}
            
            fingerprint_stats.append({
                'fingerprint_id': fp_id,
                'total_comparisons': len(rows),
                'as_idA': len(df[df['idA'] == fp_id]) if 'idA' in df.columns else 0,
                'as_idB': len(df[df['idB'] == fp_id]) if 'idB' in df.columns else 0,
                **{f'relation_{k}': v for k, v in relation_counts.items()}
            })
        
        # Salva summary generale
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_csv(self.output_dir / "aggregation_summary.csv", index=False)
        
        # Salva statistiche per impronta
        if fingerprint_stats:
            fp_stats_df = pd.DataFrame(fingerprint_stats)
            fp_stats_df = fp_stats_df.sort_values('total_comparisons', ascending=False)
            fp_stats_df.to_csv(self.output_dir / "fingerprint_statistics.csv", index=False)
        
        print(f"✅ Report salvati in: {self.output_dir}")
    
    def print_summary(self):
        """Stampa un riassunto dell'elaborazione."""
        print("\n" + "=" * 60)
        print("RIASSUNTO AGGREGAZIONE")
        print("=" * 60)
        print(f"File CSV processati: {self.files_processed}")
        print(f"Righe totali elaborate: {self.total_rows}")
        print(f"Impronte uniche trovate: {len(self.fingerprint_data)}")
        print(f"Directory output: {self.output_dir.absolute()}")
        
        if self.fingerprint_data:
            print(f"\nTop 5 impronte per numero di confronti:")
            sorted_fps = sorted(self.fingerprint_data.items(), key=lambda x: len(x[1]), reverse=True)
            for i, (fp_id, rows) in enumerate(sorted_fps[:5], 1):
                print(f"  {i}. {fp_id}: {len(rows)} confronti")
    
    def run(self):
        """Esegue l'intera procedura di aggregazione."""
        print("=== AGGREGATORE CSV ===\n")
        
        # Setup
        self.setup_output_directory()
        
        # Scansiona e processa tutti i CSV
        if not self.scan_all_csv_files():
            return
        
        # Crea output
        self.create_unified_csv()
        self.create_fingerprint_csvs()
        self.create_summary_report()
        
        # Riassunto finale
        self.print_summary()

def main():
    """Funzione principale."""
    print("Questo script aggrega tutti i file CSV di confronto in:")
    print("1. Un CSV unificato con tutti i dati")
    print("2. CSV individuali per ogni impronta")
    print("3. Report statistici")
    print()
    
    # Conferma dall'utente
    response = input("Vuoi procedere con l'aggregazione? (s/N): ").lower()
    if response not in ['s', 'si', 'y', 'yes']:
        print("Operazione annullata.")
        return
    
    # Crea ed esegui l'aggregatore
    aggregator = CSVAggregator()
    aggregator.run()
    
    print("\n✅ Aggregazione completata!")

if __name__ == "__main__":
    main()