#!/usr/bin/env python3
"""
Script per creare statistiche complessive da all_comparisons_unified.csv
e generare tabelle LaTeX per ogni impronta.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict
import re

class UnifiedStatsGenerator:
    def __init__(self, aggregated_dir="Aggregated_Results"):
        self.aggregated_dir = Path(aggregated_dir)
        self.unified_file = self.aggregated_dir / "all_comparisons_unified.csv"
        self.output_dir = self.aggregated_dir / "unified_stats"
        
    def setup_output_directory(self):
        """Crea la directory di output."""
        self.output_dir.mkdir(exist_ok=True)
        (self.output_dir / "latex_tables").mkdir(exist_ok=True)
        
    def load_unified_data(self):
        """Carica il file unificato."""
        if not self.unified_file.exists():
            print(f"Errore: File {self.unified_file} non trovato!")
            return None
            
        try:
            df = pd.read_csv(self.unified_file)
            print(f"Caricati {len(df)} confronti dal file unificato")
            return df
        except Exception as e:
            print(f"Errore nel caricare {self.unified_file}: {e}")
            return None
    
    def get_all_fingerprints(self, df):
        """Ottiene tutte le impronte uniche dal dataset."""
        fingerprints = set()
        
        for col in ['idA', 'idB']:
            if col in df.columns:
                fingerprints.update(df[col].dropna().astype(str).unique())
        
        return sorted(list(fingerprints))
    
    def analyze_fingerprint_from_unified(self, df, fingerprint_name):
        """Analizza una specifica impronta dal dataset unificato."""
        # Filtra i dati per l'impronta specificata
        fingerprint_data = df[
            (df['idA'].astype(str) == fingerprint_name) | 
            (df['idB'].astype(str) == fingerprint_name)
        ].copy()
        
        if fingerprint_data.empty:
            return None
            
        # Raggruppa per relazione e calcola statistiche
        relations_stats = {}
        unique_relations = fingerprint_data['relation'].unique()
        
        for relation in unique_relations:
            if pd.isna(relation):
                relation_name = "UNKNOWN"
            else:
                relation_name = str(relation)
                
            relation_data = fingerprint_data[
                fingerprint_data['relation'] == relation
            ] if not pd.isna(relation) else fingerprint_data[
                pd.isna(fingerprint_data['relation'])
            ]
            
            stats = self.calculate_unified_stats(relation_data, fingerprint_name)
            relations_stats[relation_name] = stats
            
        return relations_stats
    
    def calculate_unified_stats(self, relation_data, fingerprint_name):
        """Calcola statistiche per una relazione specifica."""
        stats = {}
        
        # Trova tutte le impronte diverse da quella corrente
        other_fingerprints = set()
        matches_per_fingerprint = defaultdict(int)
        valid_scores = []
        
        for _, row in relation_data.iterrows():
            # Identifica l'altra impronta
            other_fp = None
            if str(row['idA']) == fingerprint_name:
                other_fp = str(row['idB'])
            elif str(row['idB']) == fingerprint_name:
                other_fp = str(row['idA'])
            
            if other_fp and other_fp != 'nan':
                other_fingerprints.add(other_fp)
                
                # Conta i match per questa impronta
                score = row.get('score', None)
                if pd.notna(score) and score != 0:
                    matches_per_fingerprint[other_fp] += 1
                    valid_scores.append(float(score))
        
        # Statistiche base
        stats['unique_fingerprints_total'] = len(other_fingerprints)
        stats['unique_fingerprints_with_matches'] = len(matches_per_fingerprint)
        stats['total_matches'] = len(valid_scores)
        
        # Calcola match medio per impronta con match
        if matches_per_fingerprint:
            stats['average_matches_per_fingerprint'] = np.mean(list(matches_per_fingerprint.values()))
        else:
            stats['average_matches_per_fingerprint'] = 0
        
        # Statistiche score
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
        
        # Percentuale di match
        if stats['unique_fingerprints_total'] > 0:
            stats['match_percentage'] = (stats['unique_fingerprints_with_matches'] / 
                                       stats['unique_fingerprints_total']) * 100
        else:
            stats['match_percentage'] = 0
            
        return stats
    
    def create_latex_tables(self, fingerprint_name, relations_stats):
        """Crea le tabelle LaTeX per un'impronta."""
        safe_fp_name = re.sub(r'[^a-zA-Z0-9_]', '_', fingerprint_name)
        
        # Mappa nomi relazioni per LaTeX
        relation_mapping = {
            'same_individual': 'Same Individual',
            'siblings': 'Same Family',
            'stranger': 'Stranger',
            'child_father': 'Child-Father',
            'child_mother': 'Child-Mother',
            'twins': 'Twins',
            'same_family': 'Same Family'
        }
        
        latex_content = []
        
        # Tabella 1: Statistiche di matching
        latex_content.append(f"""\\begin{{table}}[htbp]
\\centering
\\caption{{Statistiche di matching per l'impronta {fingerprint_name.replace('_', '\\_')}}}
\\label{{tab:results_{safe_fp_name}}}
\\begin{{tabular}}{{|l|c|c|c|}}
\\hline
\\textbf{{Relazione}} & \\textbf{{Impronte Totali}} & \\textbf{{Impronte con Match}} & \\textbf{{Match Totali}} \\\\
\\hline""")
        
        for relation, stats in relations_stats.items():
            display_name = relation_mapping.get(relation, relation.replace('_', ' ').title())
            latex_content.append(f"{display_name} & {stats['unique_fingerprints_total']} & {stats['unique_fingerprints_with_matches']} & {stats['total_matches']} \\\\")
            latex_content.append("\\hline")
        
        latex_content.append("""\\end{tabular}
\\end{table}

""")
        
        # Tabella 2: Percentuali e match medi
        latex_content.append(f"""\\begin{{table}}[htbp]
\\centering
\\caption{{Percentuale di impronte con match e match medio per impronta con match}}
\\label{{tab:match_percentage_{safe_fp_name}}}
\\begin{{tabular}}{{|l|c|c|}}
\\hline
\\textbf{{Relazione}} & \\textbf{{Percentuale Match}} & \\textbf{{Match Medio per Impronta con Match}} \\\\
\\hline""")
        
        for relation, stats in relations_stats.items():
            display_name = relation_mapping.get(relation, relation.replace('_', ' ').title())
            latex_content.append(f"{display_name} & {stats['match_percentage']:.2f}\\% & {stats['average_matches_per_fingerprint']:.2f} \\\\")
            latex_content.append("\\hline")
        
        latex_content.append("""\\end{tabular}
\\end{table}

""")
        
        # Tabella 3: Distribuzione score
        latex_content.append(f"""\\begin{{table}}[htbp]
\\centering
\\caption{{Distribuzione degli score per l'impronta {fingerprint_name.replace('_', '\\_')}}}
\\label{{tab:scores_{safe_fp_name}}}
\\begin{{tabular}}{{|l|c|c|c|c|}}
\\hline
\\textbf{{Relazione}} & \\textbf{{Score Max}} & \\textbf{{Score Min}} & \\textbf{{Score Medio}} & \\textbf{{Deviazione Std}} \\\\
\\hline""")
        
        for relation, stats in relations_stats.items():
            display_name = relation_mapping.get(relation, relation.replace('_', ' ').title())
            latex_content.append(f"{display_name} & {stats['score_max']:.3f} & {stats['score_min']:.3f} & {stats['score_mean']:.3f} & {stats['score_std']:.3f} \\\\")
            latex_content.append("\\hline")
        
        latex_content.append("""\\end{tabular}
\\end{table}

""")
        
        return '\n'.join(latex_content)
    
    def save_csv_stats(self, fingerprint_name, relations_stats):
        """Salva le statistiche in formato CSV."""
        stats_data = []
        
        for relation, stats in relations_stats.items():
            stats_data.append({
                'fingerprint': fingerprint_name,
                'relation': relation,
                'unique_fingerprints_total': stats['unique_fingerprints_total'],
                'unique_fingerprints_with_matches': stats['unique_fingerprints_with_matches'],
                'total_matches': stats['total_matches'],
                'average_matches_per_fingerprint': stats['average_matches_per_fingerprint'],
                'match_percentage': stats['match_percentage'],
                'score_max': stats['score_max'],
                'score_min': stats['score_min'],
                'score_mean': stats['score_mean'],
                'score_std': stats['score_std']
            })
        
        stats_df = pd.DataFrame(stats_data)
        
        # Nome file sicuro
        safe_fp_name = re.sub(r'[^a-zA-Z0-9_]', '_', fingerprint_name)
        csv_file = self.output_dir / f"{safe_fp_name}_unified_stats.csv"
        stats_df.to_csv(csv_file, index=False)
        
        return csv_file
    
    def process_all_fingerprints(self, df, selected_fingerprints=None):
        """Processa tutte le impronte o quelle selezionate."""
        all_fingerprints = self.get_all_fingerprints(df)
        
        if selected_fingerprints:
            fingerprints_to_process = [fp for fp in selected_fingerprints if fp in all_fingerprints]
        else:
            fingerprints_to_process = all_fingerprints
        
        print(f"Processando {len(fingerprints_to_process)} impronte...")
        
        all_latex_content = []
        
        for fingerprint in fingerprints_to_process:
            print(f"Processando {fingerprint}...")
            
            relations_stats = self.analyze_fingerprint_from_unified(df, fingerprint)
            
            if relations_stats:
                # Salva CSV
                csv_file = self.save_csv_stats(fingerprint, relations_stats)
                print(f"  ✅ CSV salvato: {csv_file}")
                
                # Genera LaTeX
                latex_content = self.create_latex_tables(fingerprint, relations_stats)
                all_latex_content.append(latex_content)
                
                # Salva LaTeX individuale
                safe_fp_name = re.sub(r'[^a-zA-Z0-9_]', '_', fingerprint)
                latex_file = self.output_dir / "latex_tables" / f"{safe_fp_name}_tables.tex"
                with open(latex_file, 'w', encoding='utf-8') as f:
                    f.write(latex_content)
                print(f"  ✅ LaTeX salvato: {latex_file}")
            else:
                print(f"  ⚠️  Nessun dato trovato per {fingerprint}")
        
        # Salva file LaTeX completo
        if all_latex_content:
            complete_latex_file = self.output_dir / "all_fingerprints_tables.tex"
            with open(complete_latex_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(all_latex_content))
            print(f"\n✅ File LaTeX completo salvato: {complete_latex_file}")
    
    def interactive_selection(self, df):
        """Permette la selezione interattiva delle impronte."""
        all_fingerprints = self.get_all_fingerprints(df)
        
        print(f"\nTrovate {len(all_fingerprints)} impronte uniche.")
        print("Opzioni:")
        print("1. Processa tutte le impronte")
        print("2. Seleziona impronte specifiche")
        print("3. Processa solo alcune impronte (inserisci pattern)")
        
        choice = input("\nScegli un'opzione (1-3): ").strip()
        
        if choice == "1":
            return all_fingerprints
        elif choice == "2":
            print("\nImpronte disponibili:")
            for i, fp in enumerate(all_fingerprints, 1):
                print(f"{i:3d}. {fp}")
            
            indices = input("\nInserisci i numeri delle impronte (separati da virgola): ")
            try:
                selected_indices = [int(x.strip()) - 1 for x in indices.split(',')]
                return [all_fingerprints[i] for i in selected_indices if 0 <= i < len(all_fingerprints)]
            except:
                print("Selezione non valida, processando tutte.")
                return all_fingerprints
        elif choice == "3":
            pattern = input("Inserisci pattern (es. '01_', '02_Ax'): ").strip()
            return [fp for fp in all_fingerprints if pattern in fp]
        else:
            return all_fingerprints
    
    def run(self):
        """Esegue l'analisi completa."""
        print("=== GENERATORE STATISTICHE UNIFICATE ===\n")
        
        # Setup
        self.setup_output_directory()
        
        # Carica dati
        df = self.load_unified_data()
        if df is None:
            return
        
        # Selezione impronte
        selected_fingerprints = self.interactive_selection(df)
        
        if not selected_fingerprints:
            print("Nessuna impronta selezionata.")
            return
        
        # Processamento
        self.process_all_fingerprints(df, selected_fingerprints)
        
        print(f"\n✅ Elaborazione completata!")
        print(f"Output salvato in: {self.output_dir}")

def main():
    """Funzione principale."""
    generator = UnifiedStatsGenerator()
    generator.run()

if __name__ == "__main__":
    main()