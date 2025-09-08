#!/usr/bin/env python3
import os
import csv
import json
from collections import defaultdict
import glob

def get_fingerprint_code_from_csv(csv_file):
    """
    Estrae il codice dell'impronta (idA) dal primo record del CSV.
    """
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            first_row = next(reader, None)
            if first_row and 'idA' in first_row:
                return first_row['idA']
    except Exception:
        pass
    return None

def analyze_fingerprint_comparisons(base_comparisons_dir):
    """
    Analizza tutti i confronti in All_comparisons/ e genera statistiche per ogni impronta.
    Struttura: All_comparisons/{fingerprint_id}/run_{timestamp}/{fingerprint_name}.csv
    """
    
    fingerprint_stats = {}
    
    # Naviga tutte le cartelle numeriche (0, 1, 2, ...)
    for fingerprint_id in sorted(os.listdir(base_comparisons_dir)):
        fingerprint_path = os.path.join(base_comparisons_dir, fingerprint_id)
        
        if not os.path.isdir(fingerprint_path):
            continue
            
        print(f"Elaborando impronta {fingerprint_id}...")
        
        # Inizializza le statistiche per questa impronta
        stats = {
            'fingerprint_id': fingerprint_id,
            'fingerprint_code': None,  # Verrà determinato dal primo CSV trovato
            'total_comparisons': 0,
            'total_matches': 0,
            'category_stats': defaultdict(lambda: {'comparisons': 0, 'matches': 0, 'scores': []}),
            'relation_stats': defaultdict(lambda: {'comparisons': 0, 'matches': 0, 'scores': []})
        }
        
        # Naviga tutti i run di questa impronta
        for run_folder in os.listdir(fingerprint_path):
            run_path = os.path.join(fingerprint_path, run_folder)
            
            if not os.path.isdir(run_path):
                continue
                
            # Trova tutti i CSV in questo run
            csv_files = glob.glob(os.path.join(run_path, "*.csv"))
            
            for csv_file in csv_files:
                # Estrae il nome dell'impronta target dal nome del file
                target_fingerprint = os.path.basename(csv_file).replace('.csv', '')
                
                # Determina il fingerprint_code dalla prima riga del CSV (se non già determinato)
                if stats['fingerprint_code'] is None:
                    stats['fingerprint_code'] = get_fingerprint_code_from_csv(csv_file)
                
                # Determina la categoria basandosi sul prefisso del nome dell'impronta
                category = determine_category(target_fingerprint)
                
                try:
                    with open(csv_file, 'r') as f:
                        reader = csv.DictReader(f)
                        
                        for row in reader:
                            # Statistiche totali
                            stats['total_comparisons'] += 1
                            
                            # Estrae le informazioni dalla riga
                            relation = row.get('relation', 'unknown')
                            score_str = row.get('score', '0').strip()
                            
                            # Gestisce i casi di score vuoti o non validi
                            try:
                                score = float(score_str) if score_str else 0.0
                            except (ValueError, TypeError):
                                score = 0.0
                            
                            # Considera un match se il punteggio è > 0.5 (soglia configurabile)
                            is_match = score > 0.5
                            if is_match:
                                stats['total_matches'] += 1
                            
                            # Statistiche per categoria
                            stats['category_stats'][category]['comparisons'] += 1
                            stats['category_stats'][category]['scores'].append(score)
                            if is_match:
                                stats['category_stats'][category]['matches'] += 1
                            
                            # Statistiche per tipo di relazione
                            stats['relation_stats'][relation]['comparisons'] += 1
                            stats['relation_stats'][relation]['scores'].append(score)
                            if is_match:
                                stats['relation_stats'][relation]['matches'] += 1
                                
                except Exception as e:
                    print(f"Errore leggendo {csv_file}: {e}")
                    continue
        
        fingerprint_stats[fingerprint_id] = stats
    
    return fingerprint_stats

def determine_category(fingerprint_name):
    """
    Determina la categoria dell'impronta basandosi sul prefisso del nome.
    Esempi: 01_Ay_01_00 -> categoria "01_Ay"
    """
    parts = fingerprint_name.split('_')
    if len(parts) >= 2:
        return f"{parts[0]}_{parts[1]}"
    return "unknown"

def calculate_average_scores(scores):
    """Calcola il punteggio medio da una lista di punteggi."""
    if not scores:
        return 0.0
    return sum(scores) / len(scores)

def generate_csv_statistics(fingerprint_stats, output_file):
    """
    Genera un file CSV con le statistiche per ogni impronta.
    """
    
    fieldnames = [
        'fingerprint_id',
        'fingerprint_code',
        'total_comparisons',
        'total_matches',
        'overall_match_rate',
        'overall_avg_score'
    ]
    
    # Trova tutte le categorie uniche
    all_categories = set()
    all_relations = set()
    
    for stats in fingerprint_stats.values():
        all_categories.update(stats['category_stats'].keys())
        all_relations.update(stats['relation_stats'].keys())
    
    # Aggiungi campi per le categorie
    for category in sorted(all_categories):
        fieldnames.extend([
            f'{category}_comparisons',
            f'{category}_matches',
            f'{category}_match_rate',
            f'{category}_avg_score'
        ])
    
    # Aggiungi campi per le relazioni
    for relation in sorted(all_relations):
        fieldnames.extend([
            f'{relation}_comparisons',
            f'{relation}_matches',
            f'{relation}_match_rate',
            f'{relation}_avg_score'
        ])
    
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for fingerprint_id, stats in sorted(fingerprint_stats.items()):
            row = {
                'fingerprint_id': fingerprint_id,
                'fingerprint_code': stats['fingerprint_code'] or 'unknown',
                'total_comparisons': stats['total_comparisons'],
                'total_matches': stats['total_matches'],
                'overall_match_rate': stats['total_matches'] / max(stats['total_comparisons'], 1),
                'overall_avg_score': calculate_average_scores([
                    score for cat_stats in stats['category_stats'].values() 
                    for score in cat_stats['scores']
                ])
            }
            
            # Statistiche per categoria
            for category in sorted(all_categories):
                cat_stats = stats['category_stats'].get(category, {'comparisons': 0, 'matches': 0, 'scores': []})
                row[f'{category}_comparisons'] = cat_stats['comparisons']
                row[f'{category}_matches'] = cat_stats['matches']
                row[f'{category}_match_rate'] = cat_stats['matches'] / max(cat_stats['comparisons'], 1)
                row[f'{category}_avg_score'] = calculate_average_scores(cat_stats['scores'])
            
            # Statistiche per relazione
            for relation in sorted(all_relations):
                rel_stats = stats['relation_stats'].get(relation, {'comparisons': 0, 'matches': 0, 'scores': []})
                row[f'{relation}_comparisons'] = rel_stats['comparisons']
                row[f'{relation}_matches'] = rel_stats['matches']
                row[f'{relation}_match_rate'] = rel_stats['matches'] / max(rel_stats['comparisons'], 1)
                row[f'{relation}_avg_score'] = calculate_average_scores(rel_stats['scores'])
            
            writer.writerow(row)

def main():
    base_comparisons_dir = "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons"
    output_file = "/Users/riccardotortorelli/Desktop/Tesi/fingerprint_statistics.csv"
    
    print("Inizio analisi delle statistiche delle impronte...")
    print(f"Directory base: {base_comparisons_dir}")
    
    if not os.path.exists(base_comparisons_dir):
        print(f"Errore: La directory {base_comparisons_dir} non esiste!")
        return
    
    # Analizza tutti i confronti
    fingerprint_stats = analyze_fingerprint_comparisons(base_comparisons_dir)
    
    if not fingerprint_stats:
        print("Nessuna statistica trovata!")
        return
    
    print(f"Trovate statistiche per {len(fingerprint_stats)} impronte")
    
    # Genera il CSV
    generate_csv_statistics(fingerprint_stats, output_file)
    
    print(f"Statistiche salvate in: {output_file}")
    
    # Mostra un riassunto
    total_fingerprints = len(fingerprint_stats)
    total_comparisons = sum(stats['total_comparisons'] for stats in fingerprint_stats.values())
    total_matches = sum(stats['total_matches'] for stats in fingerprint_stats.values())
    
    print(f"\nRiassunto:")
    print(f"- Impronte analizzate: {total_fingerprints}")
    print(f"- Confronti totali: {total_comparisons}")
    print(f"- Match totali: {total_matches}")
    print(f"- Tasso di match globale: {total_matches/max(total_comparisons, 1):.3f}")

if __name__ == "__main__":
    main()