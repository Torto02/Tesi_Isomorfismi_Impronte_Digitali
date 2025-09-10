#!/usr/bin/env python3
"""
Script per creare statistiche globali da tutti i confronti.
Genera tabelle complessive per tutte le relazioni basate su all_comparisons_unified.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict

class GlobalStatsGenerator:
    def __init__(self, aggregated_dir="Aggregated_Results"):
        self.aggregated_dir = Path(aggregated_dir)
        self.unified_file = self.aggregated_dir / "all_comparisons_unified.csv"
        self.output_dir = self.aggregated_dir / "global_stats"
        
    def setup_output_directory(self):
        """Crea la directory di output."""
        self.output_dir.mkdir(exist_ok=True)
        
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
    
    def analyze_global_stats(self, df):
        """Analizza le statistiche globali per tutte le relazioni."""
        print("\nAnalizzando statistiche globali...")
        
        # Raggruppa per relazione
        relations_stats = {}
        unique_relations = df['relation'].dropna().unique()
        
        for relation in unique_relations:
            relation_data = df[df['relation'] == relation]
            stats = self.calculate_global_relation_stats(relation_data, relation)
            relations_stats[relation] = stats
            
        return relations_stats
    
    def calculate_global_relation_stats(self, relation_data, relation_name):
        """Calcola statistiche globali per una relazione specifica."""
        stats = {}
        stats['relation'] = relation_name
        
        # 1) Numero di impronte confrontate per ogni relazione
        # Conta coppie uniche di impronte (A,B) e (B,A) come lo stesso confronto
        unique_pairs = set()
        confronts_with_matches = set()
        total_matches = 0
        all_scores = []
        
        for _, row in relation_data.iterrows():
            idA = str(row['idA'])
            idB = str(row['idB'])
            
            # Crea una coppia ordinata per evitare duplicati (A,B) = (B,A)
            pair = tuple(sorted([idA, idB]))
            unique_pairs.add(pair)
            
            # Controlla se questo confronto ha almeno un match
            score = row.get('score', None)
            if pd.notna(score) and score != 0:
                confronts_with_matches.add(pair)
                total_matches += 1
                all_scores.append(float(score))
        
        # 2) Numero di impronte confrontate (coppie uniche)
        stats['unique_comparisons'] = len(unique_pairs)
        
        # 3) Numero di confronti in cui si è trovato almeno un match
        stats['comparisons_with_matches'] = len(confronts_with_matches)
        
        # 4) Totale match
        stats['total_matches'] = total_matches
        
        # 5) Percentuale di match per relazione (confronti con match / confronti totali)
        if stats['unique_comparisons'] > 0:
            stats['match_percentage'] = (stats['comparisons_with_matches'] / stats['unique_comparisons']) * 100
        else:
            stats['match_percentage'] = 0
        
        # 6) Percentuale di match medio per ogni confronto (match totali / confronti con match)
        if stats['comparisons_with_matches'] > 0:
            stats['average_matches_per_comparison'] = stats['total_matches'] / stats['comparisons_with_matches']
        else:
            stats['average_matches_per_comparison'] = 0
        
        # Statistiche score aggiuntive
        if all_scores:
            stats['score_mean'] = np.mean(all_scores)
            stats['score_std'] = np.std(all_scores)
            stats['score_max'] = max(all_scores)
            stats['score_min'] = min(all_scores)
        else:
            stats['score_mean'] = 0
            stats['score_std'] = 0
            stats['score_max'] = 0
            stats['score_min'] = 0
            
        return stats
    
    def create_summary_tables(self, relations_stats):
        """Crea le tabelle riassuntive."""
        # Prepara i dati per le tabelle
        table1_data = []
        table2_data = []
        
        # Ordina le relazioni per numero di confronti
        sorted_relations = sorted(relations_stats.items(), 
                                key=lambda x: x[1]['unique_comparisons'], 
                                reverse=True)
        
        for relation_name, stats in sorted_relations:
            # Tabella 1: Confronti e Match
            table1_data.append({
                'Relazione': relation_name,
                'Confronti Totali': stats['unique_comparisons'],
                'Confronti con Match': stats['comparisons_with_matches'],
                'Match Totali': stats['total_matches']
            })
            
            # Tabella 2: Percentuali
            table2_data.append({
                'Relazione': relation_name,
                'Percentuale Confronti con Match': f"{stats['match_percentage']:.2f}%",
                'Match Medio per Confronto con Match': f"{stats['average_matches_per_comparison']:.2f}"
            })
        
        table1_df = pd.DataFrame(table1_data)
        table2_df = pd.DataFrame(table2_data)
        
        return table1_df, table2_df
    
    def create_detailed_stats_table(self, relations_stats):
        """Crea una tabella con tutte le statistiche dettagliate."""
        detailed_data = []
        
        # Ordina le relazioni
        sorted_relations = sorted(relations_stats.items(), 
                                key=lambda x: x[1]['unique_comparisons'], 
                                reverse=True)
        
        for relation_name, stats in sorted_relations:
            detailed_data.append({
                'Relazione': relation_name,
                'Confronti_Totali': stats['unique_comparisons'],
                'Confronti_con_Match': stats['comparisons_with_matches'],
                'Match_Totali': stats['total_matches'],
                'Percentuale_Confronti_con_Match': stats['match_percentage'],
                'Match_Medio_per_Confronto': stats['average_matches_per_comparison'],
                'Score_Medio': stats['score_mean'],
                'Score_Std': stats['score_std'],
                'Score_Max': stats['score_max'],
                'Score_Min': stats['score_min']
            })
        
        return pd.DataFrame(detailed_data)
    
    def create_latex_tables(self, table1_df, table2_df):
        """Crea le tabelle in formato LaTeX."""
        
        # Mappa nomi relazioni per LaTeX
        relation_mapping = {
            'same_individual': 'Same Individual',
            'siblings': 'Siblings',
            'stranger': 'Stranger',
            'child_father': 'Child-Father',
            'child_mother': 'Child-Mother',
            'twins': 'Twins',
            'same_family': 'Same Family'
        }
        
        latex_content = []
        
        # Tabella 1: Confronti e Match
        latex_content.append("""\\begin{table}[htbp]
\\centering
\\caption{Statistiche globali di confronto per relazione}
\\label{tab:global_comparisons}
\\begin{tabular}{|l|c|c|c|}
\\hline
\\textbf{Relazione} & \\textbf{Confronti Totali} & \\textbf{Confronti con Match} & \\textbf{Match Totali} \\\\
\\hline""")
        
        for _, row in table1_df.iterrows():
            relation_display = relation_mapping.get(row['Relazione'], row['Relazione'].replace('_', ' ').title())
            latex_content.append(f"{relation_display} & {row['Confronti Totali']} & {row['Confronti con Match']} & {row['Match Totali']} \\\\")
            latex_content.append("\\hline")
        
        latex_content.append("""\\end{tabular}
\\end{table}

""")
        
        # Tabella 2: Percentuali
        latex_content.append("""\\begin{table}[htbp]
\\centering
\\caption{Percentuali di match globali per relazione}
\\label{tab:global_percentages}
\\begin{tabular}{|l|c|c|}
\\hline
\\textbf{Relazione} & \\textbf{\\% Confronti con Match} & \\textbf{Match Medio per Confronto} \\\\
\\hline""")
        
        for _, row in table2_df.iterrows():
            relation_display = relation_mapping.get(row['Relazione'], row['Relazione'].replace('_', ' ').title())
            latex_content.append(f"{relation_display} & {row['Percentuale Confronti con Match']} & {row['Match Medio per Confronto con Match']} \\\\")
            latex_content.append("\\hline")
        
        latex_content.append("""\\end{tabular}
\\end{table}

""")
        
        return '\n'.join(latex_content)
    
    def print_summary_tables(self, table1_df, table2_df):
        """Stampa le tabelle riassuntive a console."""
        print("\n" + "="*80)
        print("TABELLA 1: CONFRONTI E MATCH PER RELAZIONE")
        print("="*80)
        print(table1_df.to_string(index=False))
        
        print("\n" + "="*80)
        print("TABELLA 2: PERCENTUALI DI MATCH PER RELAZIONE")
        print("="*80)
        print(table2_df.to_string(index=False))
    
    def save_results(self, table1_df, table2_df, detailed_df, latex_content):
        """Salva tutti i risultati."""
        
        # Salva CSV
        table1_df.to_csv(self.output_dir / "global_comparisons_summary.csv", index=False)
        table2_df.to_csv(self.output_dir / "global_percentages_summary.csv", index=False)
        detailed_df.to_csv(self.output_dir / "global_detailed_stats.csv", index=False)
        
        # Salva LaTeX
        with open(self.output_dir / "global_tables.tex", 'w', encoding='utf-8') as f:
            f.write(latex_content)
        
        print(f"\n✅ Risultati salvati in: {self.output_dir}")
        print(f"  - global_comparisons_summary.csv")
        print(f"  - global_percentages_summary.csv")
        print(f"  - global_detailed_stats.csv")
        print(f"  - global_tables.tex")
    
    def run(self):
        """Esegue l'analisi completa."""
        print("=== GENERATORE STATISTICHE GLOBALI ===\n")
        
        # Setup
        self.setup_output_directory()
        
        # Carica dati
        df = self.load_unified_data()
        if df is None:
            return
        
        # Analizza statistiche globali
        relations_stats = self.analyze_global_stats(df)
        
        # Crea tabelle
        table1_df, table2_df = self.create_summary_tables(relations_stats)
        detailed_df = self.create_detailed_stats_table(relations_stats)
        
        # Crea LaTeX
        latex_content = self.create_latex_tables(table1_df, table2_df)
        
        # Mostra risultati
        self.print_summary_tables(table1_df, table2_df)
        
        # Salva risultati
        self.save_results(table1_df, table2_df, detailed_df, latex_content)
        
        # Statistiche aggiuntive
        total_comparisons = sum(stats['unique_comparisons'] for stats in relations_stats.values())
        total_matches = sum(stats['total_matches'] for stats in relations_stats.values())
        
        print(f"\n" + "="*50)
        print("STATISTICHE COMPLESSIVE")
        print("="*50)
        print(f"Relazioni analizzate: {len(relations_stats)}")
        print(f"Confronti totali: {total_comparisons:,}")
        print(f"Match totali: {total_matches:,}")
        print(f"Match medio per confronto: {total_matches/total_comparisons:.2f}" if total_comparisons > 0 else "Match medio per confronto: 0")

def main():
    """Funzione principale."""
    generator = GlobalStatsGenerator()
    generator.run()
    print("\n✅ Analisi globale completata!")

if __name__ == "__main__":
    main()