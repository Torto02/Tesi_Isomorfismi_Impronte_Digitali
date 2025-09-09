#!/usr/bin/env python3
"""
Script per analizzare le statistiche delle impronte digitali.
Permette di scegliere una macro cartella e calcola statistiche sui match trovati.
"""

import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime

class FingerprintStatisticsAnalyzer:
    def __init__(self, base_dir="/Users/riccardotortorelli/Desktop/Tesi/All_comparisons"):
        self.base_dir = Path(base_dir)
        self.relations_mapping = {
            # Macro categorie
            'same_individual': 'same_individual',
            'same_family': 'same_family', 
            'twins': 'same_family',
            'siblings': 'same_family',
            'child_father': 'same_family',
            'stranger': 'stranger'
        }
        
    def get_available_directories(self):
        """Ottiene tutte le directory numeriche disponibili."""
        directories = []
        for item in self.base_dir.iterdir():
            if item.is_dir() and item.name.isdigit():
                directories.append(int(item.name))
        return sorted(directories)
    
    def get_fingerprints_in_directory(self, dir_num):
        """Ottiene tutte le impronte in una directory specifica."""
        dir_path = self.base_dir / str(dir_num)
        fingerprints = []
        if dir_path.exists():
            for item in dir_path.iterdir():
                if item.is_dir():
                    fingerprints.append(item.name)
        return sorted(fingerprints)
    
    def choose_analysis_mode(self):
        """Interfaccia interattiva per scegliere la modalità di analisi."""
        print("=== ANALISI STATISTICHE IMPRONTE DIGITALI ===\n")
        
        # Mostra le directory disponibili
        directories = self.get_available_directories()
        print("Directory disponibili:")
        for i, dir_num in enumerate(directories):
            if i % 10 == 0 and i > 0:
                print()  # Nuova linea ogni 10 elementi
            print(f"{dir_num:2d}", end="  ")
        print(f"\n\nTotale: {len(directories)} directory\n")
        
        # Scegli directory
        while True:
            try:
                chosen_dir = int(input("Inserisci il numero della directory da analizzare: "))
                if chosen_dir in directories:
                    break
                else:
                    print(f"Errore: La directory {chosen_dir} non esiste.")
            except ValueError:
                print("Errore: Inserisci un numero valido.")
        
        # Scegli modalità di analisi
        print(f"\nModalità di analisi per la directory {chosen_dir}:")
        print("1. Analizza una singola impronta specifica")
        print("2. Analizza tutte le impronte nella directory (raccomandato)")
        
        while True:
            try:
                mode = int(input("Scegli modalità (1 o 2): "))
                if mode in [1, 2]:
                    break
                else:
                    print("Errore: Inserisci 1 o 2.")
            except ValueError:
                print("Errore: Inserisci un numero valido.")
        
        if mode == 1:
            # Mostra le impronte nella directory scelta
            fingerprints = self.get_fingerprints_in_directory(chosen_dir)
            print(f"\nImpronte disponibili nella directory {chosen_dir}:")
            for i, fingerprint in enumerate(fingerprints):
                print(f"{i+1:2d}. {fingerprint}")
            print(f"\nTotale: {len(fingerprints)} impronte\n")
            
            # Scegli impronta
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
            
            return chosen_dir, chosen_fingerprint, 'single'
        else:
            return chosen_dir, None, 'directory'
    
    def analyze_fingerprint_data(self, dir_num, target_fingerprint):
        """Analizza i dati per una specifica impronta."""
        fingerprint_path = self.base_dir / str(dir_num) / target_fingerprint
        csv_files = list(fingerprint_path.glob("*.csv"))
        
        if not csv_files:
            print(f"Nessun file CSV trovato per {target_fingerprint}")
            return None, None
            
        # Statistiche dettagliate per relazione
        detailed_stats = defaultdict(lambda: {
            'total_comparisons': 0,
            'matches_found': 0,
            'total_score': 0.0,
            'scores': [],
            'subgraph_ids': []
        })
        
        # Statistiche macro per categoria
        macro_stats = defaultdict(lambda: {
            'total_comparisons': 0,
            'matches_found': 0,
            'total_score': 0.0,
            'scores': []
        })
        
        total_comparisons = 0
        total_matches = 0
        
        print(f"\nAnalizzando {len(csv_files)} file CSV per {target_fingerprint}...")
        
        for csv_file in csv_files:
            try:
                with open(csv_file, 'r', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    rows = list(reader)
                    
                    if not rows:
                        # Se non ci sono dati, è comunque un confronto senza match
                        filename = csv_file.stem
                        relation = self.infer_relation_from_filename(filename, target_fingerprint)
                        detailed_stats[relation]['total_comparisons'] += 1
                        macro_category = self.relations_mapping.get(relation, 'unknown')
                        macro_stats[macro_category]['total_comparisons'] += 1
                        total_comparisons += 1
                        continue
                    
                    for row in rows:
                        if not row.get('relation'):
                            continue
                            
                        relation = row['relation'].strip()
                        total_comparisons += 1
                        
                        # Statistiche dettagliate
                        detailed_stats[relation]['total_comparisons'] += 1
                        
                        # Macro categoria
                        macro_category = self.relations_mapping.get(relation, 'unknown')
                        macro_stats[macro_category]['total_comparisons'] += 1
                        
                        # Se c'è un subgraph_id, è un match
                        if row.get('subgraph_id') and row['subgraph_id'].strip():
                            detailed_stats[relation]['matches_found'] += 1
                            macro_stats[macro_category]['matches_found'] += 1
                            total_matches += 1
                            
                            # Score
                            if row.get('score') and row['score'].strip():
                                try:
                                    score = float(row['score'])
                                    detailed_stats[relation]['total_score'] += score
                                    detailed_stats[relation]['scores'].append(score)
                                    macro_stats[macro_category]['total_score'] += score
                                    macro_stats[macro_category]['scores'].append(score)
                                except ValueError:
                                    pass
                            
                            # Subgraph ID
                            if row.get('subgraph_id'):
                                detailed_stats[relation]['subgraph_ids'].append(row['subgraph_id'])
                        
            except Exception as e:
                print(f"Errore leggendo {csv_file}: {e}")
                continue
        
        return detailed_stats, macro_stats
    
    def analyze_full_directory(self, dir_num):
        """Analizza tutte le impronte in una directory per ottenere statistiche complete."""
        dir_path = self.base_dir / str(dir_num)
        fingerprints = self.get_fingerprints_in_directory(dir_num)
        
        if not fingerprints:
            print(f"Nessuna impronta trovata nella directory {dir_num}")
            return None, None
        
        print(f"Analizzando {len(fingerprints)} impronte nella directory {dir_num}...")
        
        # Statistiche aggregate per tutta la directory
        detailed_stats = defaultdict(lambda: {
            'total_comparisons': 0,
            'matches_found': 0,
            'total_score': 0.0,
            'scores': [],
            'subgraph_ids': []
        })
        
        macro_stats = defaultdict(lambda: {
            'total_comparisons': 0,
            'matches_found': 0,
            'total_score': 0.0,
            'scores': []
        })
        
        # Analizza ogni impronta
        for i, fingerprint in enumerate(fingerprints, 1):
            if i % 10 == 0 or i == len(fingerprints):
                print(f"  Progresso: {i}/{len(fingerprints)} impronte analizzate")
            
            fingerprint_path = dir_path / fingerprint
            csv_files = list(fingerprint_path.glob("*.csv"))
            
            for csv_file in csv_files:
                try:
                    with open(csv_file, 'r', encoding='utf-8') as file:
                        reader = csv.DictReader(file)
                        rows = list(reader)
                        
                        if not rows:
                            # Nessun dato - inferisci relazione dal filename
                            relation = self.infer_relation_from_filename(csv_file.stem, fingerprint)
                            detailed_stats[relation]['total_comparisons'] += 1
                            macro_category = self.relations_mapping.get(relation, 'unknown')
                            macro_stats[macro_category]['total_comparisons'] += 1
                            continue
                        
                        for row in rows:
                            if not row.get('relation'):
                                continue
                                
                            relation = row['relation'].strip()
                            
                            # Statistiche dettagliate
                            detailed_stats[relation]['total_comparisons'] += 1
                            
                            # Macro categoria
                            macro_category = self.relations_mapping.get(relation, 'unknown')
                            macro_stats[macro_category]['total_comparisons'] += 1
                            
                            # Se c'è un subgraph_id, è un match
                            if row.get('subgraph_id') and row['subgraph_id'].strip():
                                detailed_stats[relation]['matches_found'] += 1
                                macro_stats[macro_category]['matches_found'] += 1
                                
                                # Score
                                if row.get('score') and row['score'].strip():
                                    try:
                                        score = float(row['score'])
                                        detailed_stats[relation]['total_score'] += score
                                        detailed_stats[relation]['scores'].append(score)
                                        macro_stats[macro_category]['total_score'] += score
                                        macro_stats[macro_category]['scores'].append(score)
                                    except ValueError:
                                        pass
                                
                                # Subgraph ID
                                if row.get('subgraph_id'):
                                    detailed_stats[relation]['subgraph_ids'].append(row['subgraph_id'])
                        
                except Exception as e:
                    print(f"    Errore leggendo {csv_file}: {e}")
                    continue
        
        return detailed_stats, macro_stats
    
    def infer_relation_from_filename(self, filename, target_fingerprint):
        """Inferisce la relazione dal nome del file quando i dati CSV sono vuoti."""
        # Logica semplificata basata sui pattern dei nomi
        if filename == target_fingerprint:
            return 'same_individual'
        
        target_parts = target_fingerprint.split('_')
        filename_parts = filename.split('_')
        
        if len(target_parts) >= 2 and len(filename_parts) >= 2:
            if target_parts[0] == filename_parts[0] and target_parts[1] == filename_parts[1]:
                if target_parts[2] == filename_parts[2]:
                    return 'same_individual'
                else:
                    return 'twins'
            elif target_parts[0] == filename_parts[0]:
                return 'same_family'
        
        return 'stranger'
    
    def calculate_statistics_summary(self, stats):
        """Calcola statistiche riassuntive."""
        summary = {}
        for relation, data in stats.items():
            total_comp = data['total_comparisons']
            matches = data['matches_found']
            scores = data['scores']
            
            # Calcola il numero di impronte uniche che hanno avuto almeno un match
            unique_fingerprints_with_matches = len(set(data.get('subgraph_ids', []))) if data.get('subgraph_ids') else 0
            
            # Il tasso di match è: impronte con almeno un match / totale impronte di quel tipo
            # Assumiamo che ogni confronto rappresenti un'impronta diversa
            match_rate = (unique_fingerprints_with_matches / total_comp * 100) if total_comp > 0 else 0
            
            summary[relation] = {
                'total_comparisons': total_comp,
                'matches_found': matches,
                'unique_fingerprints_with_matches': unique_fingerprints_with_matches,
                'match_rate': match_rate,
                'avg_score': (sum(scores) / len(scores)) if scores else 0,
                'max_score': max(scores) if scores else 0,
                'min_score': min(scores) if scores else 0,
                'total_subgraphs': len(data.get('subgraph_ids', []))
            }
        return summary
    
    def save_detailed_statistics(self, detailed_stats, output_file):
        """Salva le statistiche dettagliate in CSV."""
        summary = self.calculate_statistics_summary(detailed_stats)
        
        rows = []
        for relation, stats in summary.items():
            rows.append({
                'Relation': relation,
                'Total_Comparisons': stats['total_comparisons'],
                'Matches_Found': stats['matches_found'],
                'Match_Rate_Percent': round(stats['match_rate'], 2),
                'Average_Score': round(stats['avg_score'], 4),
                'Max_Score': round(stats['max_score'], 4),
                'Min_Score': round(stats['min_score'], 4),
                'Total_Subgraphs': stats['total_subgraphs']
            })
        
        # Ordina per match rate decrescente
        rows.sort(key=lambda x: x['Match_Rate_Percent'], reverse=True)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as file:
            fieldnames = ['Relation', 'Total_Comparisons', 'Matches_Found', 
                         'Match_Rate_Percent', 'Average_Score', 'Max_Score', 
                         'Min_Score', 'Total_Subgraphs']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    
    def save_macro_statistics(self, macro_stats, output_file):
        """Salva le statistiche macro in CSV."""
        summary = self.calculate_statistics_summary(macro_stats)
        
        rows = []
        for category, stats in summary.items():
            rows.append({
                'Macro_Category': category,
                'Total_Comparisons': stats['total_comparisons'],
                'Matches_Found': stats['matches_found'],
                'Match_Rate_Percent': round(stats['match_rate'], 2),
                'Average_Score': round(stats['avg_score'], 4),
                'Max_Score': round(stats['max_score'], 4),
                'Min_Score': round(stats['min_score'], 4)
            })
        
        # Ordina per match rate decrescente
        rows.sort(key=lambda x: x['Match_Rate_Percent'], reverse=True)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as file:
            fieldnames = ['Macro_Category', 'Total_Comparisons', 'Matches_Found', 
                         'Match_Rate_Percent', 'Average_Score', 'Max_Score', 'Min_Score']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    
    def print_summary(self, detailed_stats, macro_stats, target_fingerprint):
        """Stampa un riassunto delle statistiche."""
        print(f"\n=== STATISTICHE PER {target_fingerprint} ===\n")
        
        # Statistiche macro
        print("STATISTICHE MACRO CATEGORIE:")
        macro_summary = self.calculate_statistics_summary(macro_stats)
        for category, stats in sorted(macro_summary.items(), 
                                    key=lambda x: x[1]['match_rate'], reverse=True):
            print(f"{category:15s}: {stats['matches_found']:4d}/{stats['total_comparisons']:4d} "
                  f"({stats['match_rate']:5.1f}%) - Avg Score: {stats['avg_score']:.4f}")
        
        print("\nSTATISTICHE DETTAGLIATE PER RELAZIONE:")
        detailed_summary = self.calculate_statistics_summary(detailed_stats)
        for relation, stats in sorted(detailed_summary.items(), 
                                    key=lambda x: x[1]['match_rate'], reverse=True):
            print(f"{relation:15s}: {stats['matches_found']:4d}/{stats['total_comparisons']:4d} "
                  f"({stats['match_rate']:5.1f}%) - Avg Score: {stats['avg_score']:.4f}")
    
    def run(self):
        """Esegue l'analisi completa."""
        try:
            # Scegli modalità di analisi
            dir_num, target_fingerprint, mode = self.choose_analysis_mode()
            
            # Crea timestamp per i file output
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if mode == 'single':
                print(f"\nAnalizzando l'impronta: {target_fingerprint} nella directory {dir_num}")
                
                # Analizza i dati per singola impronta
                detailed_stats, macro_stats = self.analyze_fingerprint_data(dir_num, target_fingerprint)
                
                if detailed_stats is None:
                    print("Errore nell'analisi dei dati.")
                    return
                
                # Salva le statistiche
                detailed_output = f"detailed_statistics_{target_fingerprint}_{timestamp}.csv"
                macro_output = f"macro_statistics_{target_fingerprint}_{timestamp}.csv"
                analysis_target = target_fingerprint
                
            else:  # mode == 'directory'
                print(f"\nAnalizzando tutte le impronte nella directory {dir_num}")
                
                # Analizza tutti i dati della directory
                detailed_stats, macro_stats = self.analyze_full_directory(dir_num)
                
                if detailed_stats is None:
                    print("Errore nell'analisi dei dati.")
                    return
                
                # Salva le statistiche
                detailed_output = f"directory_{dir_num}_detailed_statistics_{timestamp}.csv"
                macro_output = f"directory_{dir_num}_macro_statistics_{timestamp}.csv"
                analysis_target = f"Directory_{dir_num}"
            
            self.save_detailed_statistics(detailed_stats, detailed_output)
            self.save_macro_statistics(macro_stats, macro_output)
            
            # Stampa riassunto
            self.print_summary(detailed_stats, macro_stats, analysis_target)
            
            print(f"\n=== FILE GENERATI ===")
            print(f"Statistiche dettagliate: {detailed_output}")
            print(f"Statistiche macro:       {macro_output}")
            
        except KeyboardInterrupt:
            print("\n\nAnalisi interrotta dall'utente.")
        except Exception as e:
            print(f"\nErrore durante l'analisi: {e}")

def main():
    analyzer = FingerprintStatisticsAnalyzer()
    analyzer.run()

if __name__ == "__main__":
    main()