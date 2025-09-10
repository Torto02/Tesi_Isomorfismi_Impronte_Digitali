#!/usr/bin/env python3
"""
Script per analizzare le statistiche dei confronti di impronte.
Analizza i dati di confronto per una specifica impronta e genera statistiche dettagliate.
"""

import os
import pandas as pd
from pathlib import Path
import numpy as np
from collections import defaultdict

class FingerprintStatsAnalyzer:
    def __init__(self, aggregated_dir="Aggregated_Results"):
        self.aggregated_dir = Path(aggregated_dir)
        self.fingerprint_dir = self.aggregated_dir / "by_fingerprint"
        
    def get_available_fingerprints(self):
        """Ottiene la lista delle impronte disponibili."""
        if not self.fingerprint_dir.exists():
            return []
            
        csv_files = list(self.fingerprint_dir.glob("*_comparisons.csv"))
        fingerprints = []
        
        for csv_file in csv_files:
            # Estrae il nome dell'impronta dal nome del file
            fingerprint_name = csv_file.stem.replace("_comparisons", "")
            fingerprints.append(fingerprint_name)
            
        return sorted(fingerprints)
    
    def select_fingerprint(self):
        """Permette all'utente di selezionare un'impronta."""
        fingerprints = self.get_available_fingerprints()
        
        if not fingerprints:
            print(f"Nessun file di confronto trovato in {self.fingerprint_dir}")
            return None
            
        print("\n--- Impronte disponibili ---")
        for idx, fingerprint in enumerate(fingerprints, 1):
            print(f"{idx:3d}. {fingerprint}")
            
        try:
            choice = int(input(f"\nSeleziona un'impronta (1-{len(fingerprints)}): ")) - 1
            if 0 <= choice < len(fingerprints):
                return fingerprints[choice]
            else:
                print("Selezione non valida.")
                return None
        except ValueError:
            print("Inserisci un numero valido.")
            return None
    
    def load_fingerprint_data(self, fingerprint_name):
        """Carica i dati di confronto per l'impronta specificata."""
        csv_file = self.fingerprint_dir / f"{fingerprint_name}_comparisons.csv"
        
        if not csv_file.exists():
            print(f"File non trovato: {csv_file}")
            return None
            
        try:
            df = pd.read_csv(csv_file)
            print(f"Caricati {len(df)} confronti per l'impronta {fingerprint_name}")
            return df
        except Exception as e:
            print(f"Errore nel caricare {csv_file}: {e}")
            return None
    
    def analyze_fingerprint_stats(self, df, fingerprint_name):
        """Analizza le statistiche per l'impronta specificata."""
        print(f"\n{'='*80}")
        print(f"ANALISI STATISTICHE PER IMPRONTA: {fingerprint_name}")
        print(f"{'='*80}")
        
        # Raggruppa per relazione
        relations_stats = {}
        
        # Ottieni tutte le relazioni uniche
        unique_relations = df['relation'].unique()
        
        for relation in unique_relations:
            if pd.isna(relation):
                relation_name = "UNKNOWN"
            else:
                relation_name = str(relation)
                
            relation_data = df[df['relation'] == relation] if not pd.isna(relation) else df[pd.isna(df['relation'])]
            relations_stats[relation_name] = self.calculate_relation_stats(relation_data, fingerprint_name)
        
        # Stampa statistiche per ogni relazione
        self.print_relation_statistics(relations_stats)
        
        # Calcola percentuali di match
        self.calculate_match_percentages(relations_stats)
        
        return relations_stats
    
    def calculate_relation_stats(self, relation_data, fingerprint_name):
        """Calcola le statistiche per una specifica relazione."""
        stats = {}
        
        # 1) Nome della relazione
        stats['relation_name'] = relation_data['relation'].iloc[0] if len(relation_data) > 0 else "UNKNOWN"
        
        # 2) Impronte univoche totali (includendo valori vuoti)
        # Considera sia idA che idB, escludendo l'impronta corrente
        other_fingerprints = set()
        for _, row in relation_data.iterrows():
            if str(row['idA']) != fingerprint_name and str(row['idA']) != 'nan':
                other_fingerprints.add(str(row['idA']))
            if str(row['idB']) != fingerprint_name and str(row['idB']) != 'nan':
                other_fingerprints.add(str(row['idB']))
        
        stats['unique_fingerprints_total'] = len(other_fingerprints)
        
        # 3) Impronte con almeno un match (score non vuoto)
        fingerprints_with_matches = set()
        valid_scores = []
        
        for _, row in relation_data.iterrows():
            score = row.get('score', None)
            if pd.notna(score) and score != 0:
                valid_scores.append(float(score))
                # Aggiungi l'altra impronta (non quella corrente)
                if str(row['idA']) != fingerprint_name:
                    fingerprints_with_matches.add(str(row['idA']))
                elif str(row['idB']) != fingerprint_name:
                    fingerprints_with_matches.add(str(row['idB']))
        
        stats['unique_fingerprints_with_matches'] = len(fingerprints_with_matches)
        
        # 4) Totale match
        stats['total_matches'] = len(valid_scores)
        
        # 5) Statistiche score (escludendo valori vuoti/0)
        if valid_scores:
            stats['score_max'] = max(valid_scores)
            stats['score_min'] = min(valid_scores)
            stats['score_mean'] = np.mean(valid_scores)
            stats['score_std'] = np.std(valid_scores)
        else:
            stats['score_max'] = 0
            stats['score_min'] = 0
            stats['score_mean'] = 0
            stats['score_std'] = 0
        
        # 6) Match percentage (sarà calcolato dopo)
        stats['match_percentage'] = 0
        
        return stats
    
    def print_relation_statistics(self, relations_stats):
        """Stampa le statistiche per ogni relazione."""
        print(f"\n{'RELAZIONE':<20} {'IMPRONTE':<10} {'CON MATCH':<10} {'TOT MATCH':<10} {'SCORE MAX':<10} {'SCORE MIN':<10} {'SCORE MEDIO':<12}")
        print("-" * 92)
        
        for relation_name, stats in relations_stats.items():
            print(f"{relation_name:<20} "
                  f"{stats['unique_fingerprints_total']:<10} "
                  f"{stats['unique_fingerprints_with_matches']:<10} "
                  f"{stats['total_matches']:<10} "
                  f"{stats['score_max']:<10.4f} "
                  f"{stats['score_min']:<10.4f} "
                  f"{stats['score_mean']:<12.4f}")
    
    def calculate_match_percentages(self, relations_stats):
        """Calcola e stampa le percentuali di match."""
        print(f"\n{'='*50}")
        print("PERCENTUALI DI MATCH")
        print(f"{'='*50}")
        
        print(f"{'RELAZIONE':<20} {'IMPRONTE TOTALI':<15} {'CON MATCH':<10} {'PERCENTUALE':<12}")
        print("-" * 62)
        
        for relation_name, stats in relations_stats.items():
            total = stats['unique_fingerprints_total']
            with_matches = stats['unique_fingerprints_with_matches']
            
            if total > 0:
                percentage = (with_matches / total) * 100
            else:
                percentage = 0
                
            stats['match_percentage'] = percentage
            
            print(f"{relation_name:<20} "
                  f"{total:<15} "
                  f"{with_matches:<10} "
                  f"{percentage:<12.2f}%")
    
    def save_detailed_report(self, fingerprint_name, relations_stats, df):
        """Salva un report dettagliato in formato CSV."""
        output_dir = self.aggregated_dir / "detailed_reports"
        output_dir.mkdir(exist_ok=True)
        
        # Report riassuntivo per relazione
        summary_data = []
        for relation_name, stats in relations_stats.items():
            summary_data.append({
                'fingerprint': fingerprint_name,
                'relation': relation_name,
                'unique_fingerprints_total': stats['unique_fingerprints_total'],
                'unique_fingerprints_with_matches': stats['unique_fingerprints_with_matches'],
                'total_matches': stats['total_matches'],
                'score_max': stats['score_max'],
                'score_min': stats['score_min'],
                'score_mean': stats['score_mean'],
                'score_std': stats['score_std'],
                'match_percentage': stats['match_percentage']
            })
        
        summary_df = pd.DataFrame(summary_data)
        summary_file = output_dir / f"{fingerprint_name}_detailed_stats.csv"
        summary_df.to_csv(summary_file, index=False)
        
        print(f"\n✅ Report dettagliato salvato: {summary_file}")
        
        return summary_file
    
    def run_analysis(self):
        """Esegue l'analisi completa."""
        print("=== ANALIZZATORE STATISTICHE IMPRONTE ===")
        
        # Selezione impronta
        fingerprint_name = self.select_fingerprint()
        if not fingerprint_name:
            return
        
        # Caricamento dati
        df = self.load_fingerprint_data(fingerprint_name)
        if df is None:
            return
        
        # Analisi statistiche
        relations_stats = self.analyze_fingerprint_stats(df, fingerprint_name)
        
        # Salvataggio report
        self.save_detailed_report(fingerprint_name, relations_stats, df)
        
        # Opzione per analizzare un'altra impronta
        while True:
            choice = input("\nVuoi analizzare un'altra impronta? (s/N): ").lower()
            if choice in ['s', 'si', 'y', 'yes']:
                print("\n" + "="*80)
                fingerprint_name = self.select_fingerprint()
                if fingerprint_name:
                    df = self.load_fingerprint_data(fingerprint_name)
                    if df is not None:
                        relations_stats = self.analyze_fingerprint_stats(df, fingerprint_name)
                        self.save_detailed_report(fingerprint_name, relations_stats, df)
            else:
                break

def main():
    """Funzione principale."""
    analyzer = FingerprintStatsAnalyzer()
    analyzer.run_analysis()
    print("\n✅ Analisi completata!")

if __name__ == "__main__":
    main()