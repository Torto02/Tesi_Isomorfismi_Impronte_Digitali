#!/usr/bin/env python3
"""
Script per dividere il file combined_all_comparisons.csv in file CSV separati.
Per ogni impronta (idA) crea un nuovo CSV con colonne: idA, idB, relation, score.
"""

import pandas as pd
import os
from datetime import datetime
from pathlib import Path

class FingerprintCSVSplitter:
    def __init__(self, combined_csv_path="combined_all_comparisons.csv"):
        self.combined_csv_path = Path(combined_csv_path)
        self.output_dir = Path("fingerprint_csvs")
        self.data = None
        
    def load_combined_data(self):
        """Carica i dati dal file CSV combinato."""
        try:
            print(f"Caricando dati da {self.combined_csv_path}...")
            self.data = pd.read_csv(self.combined_csv_path)
            print(f"Dati caricati: {len(self.data)} righe totali")
            return True
        except Exception as e:
            print(f"Errore nel caricamento del file CSV: {e}")
            return False
    
    def create_output_directory(self):
        """Crea la directory di output se non esiste."""
        self.output_dir.mkdir(exist_ok=True)
        print(f"Directory di output: {self.output_dir.absolute()}")
    
    def get_unique_fingerprints(self):
        """Ottiene tutte le impronte uniche (idA) dal dataset."""
        if self.data is None or self.data.empty:
            return []
        
        unique_fingerprints = sorted(self.data['idA'].unique())
        print(f"Trovate {len(unique_fingerprints)} impronte uniche")
        return unique_fingerprints
    
    def create_fingerprint_csv(self, fingerprint_id):
        """Crea un CSV per una specifica impronta con le colonne richieste."""
        # Filtra i dati per l'impronta specifica
        fingerprint_data = self.data[self.data['idA'] == fingerprint_id].copy()
        
        if fingerprint_data.empty:
            print(f"Nessun dato trovato per l'impronta {fingerprint_id}")
            return False
        
        # Seleziona solo le colonne richieste: idA, idB, relation, score
        output_data = fingerprint_data[['idA', 'idB', 'relation', 'score']].copy()
        
        # Pulisce i dati NaN per una migliore leggibilità
        output_data['relation'] = output_data['relation'].fillna('')
        output_data['score'] = output_data['score'].fillna('')
        
        # Nome del file di output
        output_filename = self.output_dir / f"{fingerprint_id}.csv"
        
        # Salva il CSV
        try:
            output_data.to_csv(output_filename, index=False, encoding='utf-8')
            return len(output_data)
        except Exception as e:
            print(f"Errore nel salvare {output_filename}: {e}")
            return False
    
    def split_all_fingerprints(self):
        """Divide il file combinato in CSV separati per ogni impronta."""
        if not self.load_combined_data():
            return
        
        self.create_output_directory()
        unique_fingerprints = self.get_unique_fingerprints()
        
        if not unique_fingerprints:
            print("Nessuna impronta trovata nel dataset")
            return
        
        print(f"\nCreazione di {len(unique_fingerprints)} file CSV...")
        
        successful_files = 0
        total_rows_written = 0
        failed_files = []
        
        for i, fingerprint_id in enumerate(unique_fingerprints, 1):
            # Mostra progresso ogni 10 impronte
            if i % 10 == 0 or i == len(unique_fingerprints):
                print(f"Progresso: {i}/{len(unique_fingerprints)} impronte processate")
            
            rows_written = self.create_fingerprint_csv(fingerprint_id)
            
            if rows_written:
                successful_files += 1
                total_rows_written += rows_written
            else:
                failed_files.append(fingerprint_id)
        
        # Riassunto finale
        print(f"\n=== RIEPILOGO ===")
        print(f"File CSV creati con successo: {successful_files}")
        print(f"File falliti: {len(failed_files)}")
        print(f"Righe totali scritte: {total_rows_written}")
        print(f"Directory di output: {self.output_dir.absolute()}")
        
        if failed_files:
            print(f"\nImpronte con errori: {failed_files[:10]}{'...' if len(failed_files) > 10 else ''}")
        
        # Mostra alcuni esempi di file creati
        created_files = list(self.output_dir.glob("*.csv"))[:5]
        if created_files:
            print(f"\nEsempi di file creati:")
            for file_path in created_files:
                file_size = file_path.stat().st_size
                print(f"  {file_path.name} ({file_size} bytes)")
    
    def create_summary_report(self):
        """Crea un file di riepilogo con statistiche su tutti i CSV creati."""
        if not self.output_dir.exists():
            print("Directory di output non trovata")
            return
        
        csv_files = list(self.output_dir.glob("*.csv"))
        if not csv_files:
            print("Nessun file CSV trovato nella directory di output")
            return
        
        summary_data = []
        
        print(f"Creazione report di riepilogo per {len(csv_files)} file...")
        
        for csv_file in csv_files:
            try:
                # Leggi il file per ottenere statistiche
                df = pd.read_csv(csv_file)
                
                # Conta i match (righe con score non vuoto)
                matches = df['score'].notna().sum()
                total_comparisons = len(df)
                
                # Conta le relazioni uniche
                unique_relations = df['relation'].nunique()
                
                summary_data.append({
                    'fingerprint_id': csv_file.stem,
                    'total_comparisons': total_comparisons,
                    'matches_found': matches,
                    'unique_relations': unique_relations,
                    'file_size_bytes': csv_file.stat().st_size
                })
                
            except Exception as e:
                print(f"Errore leggendo {csv_file.name}: {e}")
        
        if summary_data:
            # Crea DataFrame del riepilogo
            summary_df = pd.DataFrame(summary_data)
            
            # Salva il report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            summary_file = f"fingerprint_csvs_summary_{timestamp}.csv"
            summary_df.to_csv(summary_file, index=False)
            
            print(f"\nReport di riepilogo salvato: {summary_file}")
            print(f"Statistiche complessive:")
            print(f"  - File totali: {len(summary_df)}")
            print(f"  - Confronti totali: {summary_df['total_comparisons'].sum()}")
            print(f"  - Match totali: {summary_df['matches_found'].sum()}")
            print(f"  - Dimensione totale: {summary_df['file_size_bytes'].sum()} bytes")

def main():
    """Funzione principale."""
    print("=== DIVISORE CSV IMPRONTE DIGITALI ===\n")
    
    # Controlla se il file combinato esiste
    combined_file = "combined_all_comparisons.csv"
    if not Path(combined_file).exists():
        print(f"Errore: File {combined_file} non trovato!")
        print("Assicurati che il file combined sia nella directory corrente.")
        return
    
    # Crea e esegui lo splitter
    splitter = FingerprintCSVSplitter(combined_file)
    splitter.split_all_fingerprints()
    splitter.create_summary_report()
    
    print("\nProcesso completato!")

if __name__ == "__main__":
    main()