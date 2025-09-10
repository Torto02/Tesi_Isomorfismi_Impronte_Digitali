#!/usr/bin/env python3
"""
Script per analizzare le statistiche di una singola impronta dai CSV individuali.
Genera una tabella con: Tipo Relazione, Impronte confrontate, Impronte con almeno un match, 
match totali, Match Rate (%).
"""

import pandas as pd
import os
from pathlib import Path
from datetime import datetime

class FingerprintStatsTable:
    def __init__(self, fingerprint_csvs_dir="fingerprint_csvs"):
        self.csvs_dir = Path(fingerprint_csvs_dir)
        self.relations_mapping = {
            # Macro categorie
            'same_individual': 'same_individual',
            'same_family': 'same_family', 
            'twins': 'same_family',
            'siblings': 'same_family',
            'child_father': 'same_family',
            'stranger': 'stranger'
        }
    
    def get_available_fingerprints(self):
        """Ottiene tutte le impronte disponibili dai file CSV."""
        if not self.csvs_dir.exists():
            return []
        
        csv_files = list(self.csvs_dir.glob("*.csv"))
        fingerprints = [f.stem for f in csv_files]
        return sorted(fingerprints)
    
    def analyze_fingerprint(self, fingerprint_id):
        """Analizza le statistiche per una specifica impronta."""
        csv_file = self.csvs_dir / f"{fingerprint_id}.csv"
        
        if not csv_file.exists():
            print(f"File {csv_file} non trovato!")
            return None
        
        try:
            # Carica i dati dell'impronta
            data = pd.read_csv(csv_file)
            
            if data.empty:
                print(f"Nessun dato trovato nel file {csv_file}")
                return None
            
            print(f"Analizzando impronta: {fingerprint_id}")
            print(f"Confronti totali: {len(data)}")
            print(f"Impronte univoche totali confrontate: {data['idB'].nunique()}")
            
            # Raggruppa per tipo di relazione
            stats_by_relation = {}
            
            for relation in data['relation'].unique():
                if pd.isna(relation) or relation == '':
                    continue
                    
                # Filtra i dati per questa relazione
                relation_data = data[data['relation'] == relation].copy()
                
                # Impronte univoche confrontate per questa relazione (conta idB univoci)
                impronte_univoche = relation_data['idB'].nunique()
                
                # Impronte univoche con almeno un match (idB univoci che hanno score non vuoto)
                impronte_con_match_univoche = relation_data[relation_data['score'].notna()]['idB'].nunique()
                
                # Match totali (numero di righe con score non vuoto)
                match_totali = relation_data['score'].notna().sum()
                
                # Match rate (%) basato su impronte univoche
                match_rate = (impronte_con_match_univoche / impronte_univoche * 100) if impronte_univoche > 0 else 0
                
                stats_by_relation[relation] = {
                    'impronte_confrontate': impronte_univoche,
                    'impronte_con_match': impronte_con_match_univoche,
                    'match_totali': match_totali,
                    'match_rate': match_rate
                }
            
            # Calcola anche statistiche macro (raggruppando per categoria)
            macro_stats = {}
            
            # Per le macro categorie, devo raggruppare per categoria e contare impronte univoche
            for relation in data['relation'].unique():
                if pd.isna(relation) or relation == '':
                    continue
                    
                macro_category = self.relations_mapping.get(relation, 'unknown')
                relation_data = data[data['relation'] == relation].copy()
                
                if macro_category not in macro_stats:
                    macro_stats[macro_category] = {
                        'impronte_univoche_set': set(),
                        'impronte_con_match_set': set(),
                        'match_totali': 0
                    }
                
                # Aggiungi tutte le impronte univoche per questa categoria
                macro_stats[macro_category]['impronte_univoche_set'].update(relation_data['idB'].unique())
                
                # Aggiungi le impronte con match per questa categoria
                impronte_con_match = relation_data[relation_data['score'].notna()]['idB'].unique()
                macro_stats[macro_category]['impronte_con_match_set'].update(impronte_con_match)
                
                # Aggiungi i match totali
                macro_stats[macro_category]['match_totali'] += relation_data['score'].notna().sum()
            
            # Calcola i valori finali per le macro categorie
            for category in macro_stats:
                impronte_confrontate = len(macro_stats[category]['impronte_univoche_set'])
                impronte_con_match = len(macro_stats[category]['impronte_con_match_set'])
                match_totali = macro_stats[category]['match_totali']
                
                macro_stats[category] = {
                    'impronte_confrontate': impronte_confrontate,
                    'impronte_con_match': impronte_con_match,
                    'match_totali': match_totali,
                    'match_rate': (impronte_con_match / impronte_confrontate * 100) if impronte_confrontate > 0 else 0
                }
            
            return {
                'detailed_stats': stats_by_relation,
                'macro_stats': macro_stats
            }
            
        except Exception as e:
            print(f"Errore nell'analisi di {fingerprint_id}: {e}")
            return None
    
    def print_stats_table(self, fingerprint_id, stats):
        """Stampa la tabella delle statistiche formattata."""
        if not stats:
            return
        
        print(f"\n{'='*80}")
        print(f"STATISTICHE PER IMPRONTA: {fingerprint_id}")
        print(f"{'='*80}")
        
        # Tabella dettagliata per relazione
        print("\n🔍 STATISTICHE DETTAGLIATE PER RELAZIONE:")
        print(f"{'─'*80}")
        print(f"{'Tipo Relazione':<20} {'Confrontate':<12} {'Con Match':<10} {'Match Tot.':<10} {'Match Rate (%)':<15}")
        print(f"{'─'*80}")
        
        detailed_stats = stats['detailed_stats']
        for relation in sorted(detailed_stats.keys(), key=lambda x: detailed_stats[x]['match_rate'], reverse=True):
            data = detailed_stats[relation]
            print(f"{relation:<20} {data['impronte_confrontate']:<12} {data['impronte_con_match']:<10} "
                  f"{data['match_totali']:<10} {data['match_rate']:<14.2f}")
        
        # Tabella macro categorie
        print(f"\n📊 STATISTICHE MACRO CATEGORIE:")
        print(f"{'─'*80}")
        print(f"{'Macro Categoria':<20} {'Confrontate':<12} {'Con Match':<10} {'Match Tot.':<10} {'Match Rate (%)':<15}")
        print(f"{'─'*80}")
        
        macro_stats = stats['macro_stats']
        for category in sorted(macro_stats.keys(), key=lambda x: macro_stats[x]['match_rate'], reverse=True):
            data = macro_stats[category]
            print(f"{category:<20} {data['impronte_confrontate']:<12} {data['impronte_con_match']:<10} "
                  f"{data['match_totali']:<10} {data['match_rate']:<14.2f}")
    
    def save_stats_table(self, fingerprint_id, stats, output_format='csv'):
        """Salva la tabella delle statistiche in un file."""
        if not stats:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Prepara i dati dettagliati
        detailed_rows = []
        for relation, data in stats['detailed_stats'].items():
            detailed_rows.append({
                'Impronta': fingerprint_id,
                'Tipo_Relazione': relation,
                'Impronte_Confrontate': data['impronte_confrontate'],
                'Impronte_Con_Match': data['impronte_con_match'],
                'Match_Totali': data['match_totali'],
                'Match_Rate_Percent': round(data['match_rate'], 2)
            })
        
        # Prepara i dati macro
        macro_rows = []
        for category, data in stats['macro_stats'].items():
            macro_rows.append({
                'Impronta': fingerprint_id,
                'Macro_Categoria': category,
                'Impronte_Confrontate': data['impronte_confrontate'],
                'Impronte_Con_Match': data['impronte_con_match'],
                'Match_Totali': data['match_totali'],
                'Match_Rate_Percent': round(data['match_rate'], 2)
            })
        
        if output_format == 'csv':
            # Salva statistiche dettagliate
            detailed_df = pd.DataFrame(detailed_rows)
            detailed_file = f"stats_detailed_{fingerprint_id}_{timestamp}.csv"
            detailed_df.to_csv(detailed_file, index=False)
            
            # Salva statistiche macro
            macro_df = pd.DataFrame(macro_rows)
            macro_file = f"stats_macro_{fingerprint_id}_{timestamp}.csv"
            macro_df.to_csv(macro_file, index=False)
            
            print(f"\n📁 File salvati:")
            print(f"   - {detailed_file}")
            print(f"   - {macro_file}")
    
    def run_interactive(self):
        """Esegue l'analisi in modalità interattiva."""
        print("=== ANALISI STATISTICHE IMPRONTA SINGOLA ===\n")
        
        # Ottieni impronte disponibili
        fingerprints = self.get_available_fingerprints()
        
        if not fingerprints:
            print(f"Nessun file CSV trovato nella directory {self.csvs_dir}")
            return
        
        print(f"Impronte disponibili ({len(fingerprints)} totali):")
        
        # Mostra le impronte in colonne
        for i, fingerprint in enumerate(fingerprints):
            if i % 3 == 0 and i > 0:
                print()
            print(f"{i+1:3d}. {fingerprint:20s}", end="  ")
        print(f"\n")
        
        # Selezione impronta
        while True:
            try:
                choice = int(input("Inserisci il numero dell'impronta da analizzare: "))
                if 1 <= choice <= len(fingerprints):
                    chosen_fingerprint = fingerprints[choice - 1]
                    break
                else:
                    print(f"Errore: Inserisci un numero tra 1 e {len(fingerprints)}.")
            except ValueError:
                print("Errore: Inserisci un numero valido.")
        
        # Analizza l'impronta scelta
        stats = self.analyze_fingerprint(chosen_fingerprint)
        
        if stats:
            # Stampa le statistiche
            self.print_stats_table(chosen_fingerprint, stats)
            
            # Chiede se salvare
            save = input("\nVuoi salvare le statistiche in file CSV? (s/n): ").lower().strip()
            if save in ['s', 'si', 'y', 'yes']:
                self.save_stats_table(chosen_fingerprint, stats)
        
        print(f"\nAnalisi completata!")

def main():
    """Funzione principale."""
    analyzer = FingerprintStatsTable()
    analyzer.run_interactive()

if __name__ == "__main__":
    main()