#!/usr/bin/env python3

import os
import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from collections import defaultdict, Counter
import glob
from pathlib import Path
import argparse

# CONFIGURAZIONE: Specifica qui l'indice della cartella da analizzare
FOLDER_INDEX = 0  # Cambia questo valore per analizzare cartelle diverse (0, 1, 2, etc.)

def extract_categories(fingerprint_id):
    """
    Extract category information from fingerprint ID.
    Expected format: 01_Ay_01_00, 02_B0_05_00, etc.
    Returns: (person_id, category, sub_category, index)
    """
    parts = fingerprint_id.split('_')
    if len(parts) >= 4:
        person_id = parts[0]
        category = parts[1]
        sub_category = parts[2]
        index = parts[3]
        return person_id, category, sub_category, index
    return None, None, None, None

def analyze_folder(folder_path):
    """Analyze a single comparison folder"""
    results = {
        'matches': [],
        'relations': [],
        'categories': [],
        'scores': [],
        'detailed_matches': []
    }
    
    # Process all CSV files in the folder
    csv_files = glob.glob(os.path.join(folder_path, "**/*.csv"), recursive=True)
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            for _, row in df.iterrows():
                idA, idB = row['idA'], row['idB']
                relation = row['relation'] if 'relation' in df.columns else 'unknown'
                score = row['score'] if 'score' in df.columns and pd.notna(row['score']) else 0
                
                # Extract categories
                personA, catA, subcatA, idxA = extract_categories(idA)
                personB, catB, subcatB, idxB = extract_categories(idB)
                
                match_data = {
                    'idA': idA,
                    'idB': idB,
                    'relation': relation,
                    'score': score,
                    'categoryA': catA,
                    'categoryB': catB,
                    'subcategoryA': subcatA,
                    'subcategoryB': subcatB,
                    'personA': personA,
                    'personB': personB
                }
                
                results['matches'].append(match_data)
                results['relations'].append(relation)
                results['categories'].extend([catA, catB])
                if score > 0:
                    results['scores'].append(score)
                results['detailed_matches'].append(match_data)
        except Exception as e:
            print(f"Error processing {csv_file}: {e}")
    
    return results

def create_statistics_report(results, folder_name):
    """Generate comprehensive statistics and visualizations"""
    
    # Convert to DataFrame for easier analysis
    df = pd.DataFrame(results['detailed_matches'])
    
    print(f"\n=== STATISTICHE PER CARTELLA {folder_name} ===")
    print(f"Totale confronti analizzati: {len(df)}")
    
    # Relation statistics
    print(f"\n--- STATISTICHE RELAZIONI ---")
    relation_counts = df['relation'].value_counts()
    for relation, count in relation_counts.items():
        percentage = (count / len(df)) * 100
        print(f"{relation}: {count} ({percentage:.1f}%)")
    
    # Category statistics
    print(f"\n--- STATISTICHE CATEGORIE ---")
    
    # Count total fingerprints per category
    all_categories = []
    for _, row in df.iterrows():
        if pd.notna(row['categoryA']):
            all_categories.append(row['categoryA'])
        if pd.notna(row['categoryB']):
            all_categories.append(row['categoryB'])
    
    category_counts = Counter(all_categories)
    print("Distribuzione impronte per categoria:")
    for cat, count in category_counts.most_common():
        print(f"  {cat}: {count} impronte")
    
    # Matches by category pairs
    print(f"\n--- MATCH PER COPPIA DI CATEGORIE ---")
    category_pairs = defaultdict(list)
    
    for _, row in df.iterrows():
        if pd.notna(row['categoryA']) and pd.notna(row['categoryB']):
            pair = tuple(sorted([row['categoryA'], row['categoryB']]))
            category_pairs[pair].append({
                'relation': row['relation'],
                'score': row['score']
            })
    
    for pair, matches in category_pairs.items():
        print(f"\n{pair[0]} vs {pair[1]}:")
        relations = [m['relation'] for m in matches]
        relation_stats = Counter(relations)
        scores = [m['score'] for m in matches if m['score'] > 0]
        
        print(f"  Totale confronti: {len(matches)}")
        for rel, count in relation_stats.items():
            percentage = (count / len(matches)) * 100
            print(f"  {rel}: {count} ({percentage:.1f}%)")
        
        if scores:
            print(f"  Score medio: {np.mean(scores):.3f}")
            print(f"  Score massimo: {np.max(scores):.3f}")
    
    # Score analysis
    valid_scores = df[df['score'] > 0]
    if len(valid_scores) > 0:
        print(f"\n--- ANALISI SCORE ---")
        print(f"Match con score validi: {len(valid_scores)}")
        print(f"Score medio totale: {valid_scores['score'].mean():.3f}")
        print(f"Score mediano: {valid_scores['score'].median():.3f}")
        print(f"Score massimo: {valid_scores['score'].max():.3f}")
        print(f"Score minimo: {valid_scores['score'].min():.3f}")
    
    return df, category_counts, category_pairs

def create_visualizations(df, category_counts, category_pairs, folder_name):
    """Create comprehensive visualizations"""
    
    # Set up the plotting style
    plt.style.use('seaborn-v0_8' if 'seaborn-v0_8' in plt.style.available else 'default')
    
    # Create a figure with multiple subplots
    fig = plt.figure(figsize=(20, 16))
    
    # 1. Distribution of relations
    plt.subplot(3, 3, 1)
    relation_counts = df['relation'].value_counts()
    colors = plt.cm.Set3(np.linspace(0, 1, len(relation_counts)))
    plt.pie(relation_counts.values, labels=relation_counts.index, autopct='%1.1f%%', colors=colors)
    plt.title(f'Distribuzione Relazioni - Cartella {folder_name}')
    
    # 2. Category distribution
    plt.subplot(3, 3, 2)
    categories = list(category_counts.keys())
    counts = list(category_counts.values())
    bars = plt.bar(categories, counts, color=plt.cm.tab10(np.linspace(0, 1, len(categories))))
    plt.title('Distribuzione Impronte per Categoria')
    plt.xlabel('Categoria')
    plt.ylabel('Numero Impronte')
    plt.xticks(rotation=45)
    
    # Add value labels on bars
    for bar, count in zip(bars, counts):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                str(count), ha='center', va='bottom')
    
    # 3. Score distribution
    plt.subplot(3, 3, 3)
    valid_scores = df[df['score'] > 0]['score']
    if len(valid_scores) > 0:
        plt.hist(valid_scores, bins=30, alpha=0.7, edgecolor='black')
        plt.axvline(valid_scores.mean(), color='red', linestyle='--', label=f'Media: {valid_scores.mean():.3f}')
        plt.axvline(valid_scores.median(), color='orange', linestyle='--', label=f'Mediana: {valid_scores.median():.3f}')
        plt.title('Distribuzione Score Match')
        plt.xlabel('Score')
        plt.ylabel('Frequenza')
        plt.legend()
    
    # 4. Heatmap of category pairs matches
    plt.subplot(3, 3, 4)
    categories_list = sorted(category_counts.keys())
    heatmap_data = np.zeros((len(categories_list), len(categories_list)))
    
    for (cat1, cat2), matches in category_pairs.items():
        idx1 = categories_list.index(cat1)
        idx2 = categories_list.index(cat2)
        match_count = len(matches)
        heatmap_data[idx1][idx2] = match_count
        heatmap_data[idx2][idx1] = match_count
    
    sns.heatmap(heatmap_data, xticklabels=categories_list, yticklabels=categories_list, 
                annot=True, fmt='.0f', cmap='YlOrRd')
    plt.title('Matrice Match tra Categorie')
    plt.xticks(rotation=45)
    plt.yticks(rotation=0)
    
    # 5. Relation by category comparison
    plt.subplot(3, 3, 5)
    category_relation_data = defaultdict(lambda: defaultdict(int))
    
    for _, row in df.iterrows():
        if pd.notna(row['categoryA']) and pd.notna(row['categoryB']):
            cat_pair = f"{row['categoryA']}-{row['categoryB']}"
            category_relation_data[cat_pair][row['relation']] += 1
    
    # Create stacked bar chart
    relations_list = df['relation'].unique()
    categories_pairs = list(category_relation_data.keys())[:10]  # Top 10 pairs
    
    bottom = np.zeros(len(categories_pairs))
    colors = plt.cm.tab10(np.linspace(0, 1, len(relations_list)))
    
    for i, relation in enumerate(relations_list):
        values = [category_relation_data[pair][relation] for pair in categories_pairs]
        plt.bar(categories_pairs, values, bottom=bottom, label=relation, color=colors[i])
        bottom += values
    
    plt.title('Relazioni per Coppia di Categorie')
    plt.xlabel('Coppia Categorie')
    plt.ylabel('Numero Match')
    plt.xticks(rotation=90)
    plt.legend()
    
    # 6. Score by relation type
    plt.subplot(3, 3, 6)
    score_by_relation = []
    relation_labels = []
    
    for relation in df['relation'].unique():
        relation_scores = df[(df['relation'] == relation) & (df['score'] > 0)]['score']
        if len(relation_scores) > 0:
            score_by_relation.append(relation_scores.values)
            relation_labels.append(f"{relation}\n(n={len(relation_scores)})")
    
    if score_by_relation:
        plt.boxplot(score_by_relation, tick_labels=relation_labels)
        plt.title('Distribuzione Score per Tipo Relazione')
        plt.ylabel('Score')
        plt.xticks(rotation=45)
    
    # 7. Match success rate by category
    plt.subplot(3, 3, 7)
    category_success = {}
    
    for category in categories_list:
        category_matches = df[(df['categoryA'] == category) | (df['categoryB'] == category)]
        successful_matches = category_matches[category_matches['score'] > 0]
        success_rate = len(successful_matches) / len(category_matches) * 100 if len(category_matches) > 0 else 0
        category_success[category] = success_rate
    
    categories = list(category_success.keys())
    success_rates = list(category_success.values())
    bars = plt.bar(categories, success_rates, color=plt.cm.viridis(np.linspace(0, 1, len(categories))))
    plt.title('Tasso di Successo Match per Categoria')
    plt.xlabel('Categoria')
    plt.ylabel('% Match con Score > 0')
    plt.xticks(rotation=45)
    
    # Add value labels
    for bar, rate in zip(bars, success_rates):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                f'{rate:.1f}%', ha='center', va='bottom')
    
    # 8. Average score by category
    plt.subplot(3, 3, 8)
    category_avg_score = {}
    
    for category in categories_list:
        category_matches = df[(df['categoryA'] == category) | (df['categoryB'] == category)]
        valid_scores = category_matches[category_matches['score'] > 0]['score']
        avg_score = valid_scores.mean() if len(valid_scores) > 0 else 0
        category_avg_score[category] = avg_score
    
    categories = list(category_avg_score.keys())
    avg_scores = list(category_avg_score.values())
    bars = plt.bar(categories, avg_scores, color=plt.cm.plasma(np.linspace(0, 1, len(categories))))
    plt.title('Score Medio per Categoria')
    plt.xlabel('Categoria')
    plt.ylabel('Score Medio')
    plt.xticks(rotation=45)
    
    # Add value labels
    for bar, score in zip(bars, avg_scores):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, 
                f'{score:.3f}', ha='center', va='bottom')
    
    # 9. Proportional analysis - matches relative to total fingerprints
    plt.subplot(3, 3, 9)
    proportional_matches = {}
    
    for category in categories_list:
        total_fingerprints = category_counts[category]
        category_matches = df[(df['categoryA'] == category) | (df['categoryB'] == category)]
        successful_matches = len(category_matches[category_matches['score'] > 0])
        proportion = successful_matches / total_fingerprints if total_fingerprints > 0 else 0
        proportional_matches[category] = proportion
    
    categories = list(proportional_matches.keys())
    proportions = list(proportional_matches.values())
    bars = plt.bar(categories, proportions, color=plt.cm.coolwarm(np.linspace(0, 1, len(categories))))
    plt.title('Match Riusciti / Totale Impronte per Categoria')
    plt.xlabel('Categoria')
    plt.ylabel('Rapporto Match/Impronte')
    plt.xticks(rotation=45)
    
    # Add value labels
    for bar, prop in zip(bars, proportions):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, 
                f'{prop:.2f}', ha='center', va='bottom')
    
    plt.tight_layout()
    
    # Save the plot
    output_file = f'statistics_folder_{folder_name}.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\nGrafici salvati in: {output_file}")
    
    return category_success, category_avg_score, proportional_matches

def create_detailed_tables(df, folder_name):
    """Create detailed statistical tables"""
    
    print(f"\n=== TABELLE DETTAGLIATE PER CARTELLA {folder_name} ===")
    
    # Table 1: Summary by category
    categories_list = sorted(df['categoryA'].dropna().unique().tolist() + 
                           df['categoryB'].dropna().unique().tolist())
    categories_list = sorted(list(set(categories_list)))
    
    summary_data = []
    for category in categories_list:
        cat_matches = df[(df['categoryA'] == category) | (df['categoryB'] == category)]
        total_matches = len(cat_matches)
        successful_matches = len(cat_matches[cat_matches['score'] > 0])
        avg_score = cat_matches[cat_matches['score'] > 0]['score'].mean() if successful_matches > 0 else 0
        success_rate = (successful_matches / total_matches * 100) if total_matches > 0 else 0
        
        # Count relations
        relations = cat_matches['relation'].value_counts().to_dict()
        
        summary_data.append({
            'Categoria': category,
            'Totale_Confronti': total_matches,
            'Match_Riusciti': successful_matches,
            'Tasso_Successo_%': success_rate,
            'Score_Medio': avg_score,
            'Same_Individual': relations.get('same_individual', 0),
            'Siblings': relations.get('siblings', 0),
            'Stranger': relations.get('stranger', 0)
        })
    
    summary_df = pd.DataFrame(summary_data)
    print("\nTabella riassuntiva per categoria:")
    print(summary_df.to_string(index=False, float_format=lambda x: f'{x:.3f}' if x != x//1 else f'{int(x)}'))
    
    # Save summary table
    summary_df.to_csv(f'summary_category_{folder_name}.csv', index=False)
    print(f"\nTabella salvata in: summary_category_{folder_name}.csv")
    
    # Table 2: Cross-category analysis
    print(f"\n--- ANALISI INCROCIATA TRA CATEGORIE ---")
    cross_analysis = []
    
    for i, cat1 in enumerate(categories_list):
        for j, cat2 in enumerate(categories_list):
            if i <= j:  # Avoid duplicates
                cross_matches = df[((df['categoryA'] == cat1) & (df['categoryB'] == cat2)) | 
                                 ((df['categoryA'] == cat2) & (df['categoryB'] == cat1))]
                
                if len(cross_matches) > 0:
                    total = len(cross_matches)
                    successful = len(cross_matches[cross_matches['score'] > 0])
                    avg_score = cross_matches[cross_matches['score'] > 0]['score'].mean() if successful > 0 else 0
                    
                    relations = cross_matches['relation'].value_counts().to_dict()
                    
                    cross_analysis.append({
                        'Categoria_A': cat1,
                        'Categoria_B': cat2,
                        'Totale_Confronti': total,
                        'Match_Riusciti': successful,
                        'Tasso_Successo_%': (successful/total*100) if total > 0 else 0,
                        'Score_Medio': avg_score,
                        'Same_Individual': relations.get('same_individual', 0),
                        'Siblings': relations.get('siblings', 0),
                        'Stranger': relations.get('stranger', 0)
                    })
    
    cross_df = pd.DataFrame(cross_analysis)
    cross_df = cross_df.sort_values('Tasso_Successo_%', ascending=False)
    
    print("\nAnalisi incrociata tra categorie (ordinata per tasso di successo):")
    print(cross_df.to_string(index=False, float_format=lambda x: f'{x:.2f}' if x != x//1 else f'{int(x)}'))
    
    # Save cross analysis
    cross_df.to_csv(f'cross_analysis_{folder_name}.csv', index=False)
    print(f"\nAnalisi incrociata salvata in: cross_analysis_{folder_name}.csv")
    
    return summary_df, cross_df

def main():
    # Costruisci il percorso della cartella usando l'indice specificato
    base_folder = "All_comparisons"
    folder_path = os.path.join(base_folder, str(FOLDER_INDEX))
    
    if not os.path.exists(folder_path):
        print(f"Errore: La cartella {folder_path} non esiste")
        # Prova a cercare cartelle disponibili
        if os.path.exists(base_folder):
            available_folders = [f for f in os.listdir(base_folder) 
                               if os.path.isdir(os.path.join(base_folder, f)) and f.isdigit()]
            if available_folders:
                print(f"Cartelle disponibili in {base_folder}: {sorted(available_folders)}")
                print(f"Modifica la variabile FOLDER_INDEX nel codice con uno di questi valori: {sorted(available_folders)}")
        return
    
    folder_name = os.path.basename(folder_path)
    
    print(f"Analizzando cartella: {folder_path} (indice {FOLDER_INDEX})")
    
    # Analyze the folder
    results = analyze_folder(folder_path)
    
    if not results['matches']:
        print("Nessun dato trovato nella cartella specificata")
        return
    
    # Create statistics
    df, category_counts, category_pairs = create_statistics_report(results, folder_name)
    
    # Create detailed tables
    summary_df, cross_df = create_detailed_tables(df, folder_name)
    
    # Create visualizations
    category_success, category_avg_score, proportional_matches = create_visualizations(
        df, category_counts, category_pairs, folder_name)
    
    # plt.show()  # Disabled for non-interactive mode
    
    print(f"\n=== RIEPILOGO FINALE ===")
    print(f"Cartella analizzata: {folder_name} (indice {FOLDER_INDEX})")
    print(f"Totale confronti: {len(df)}")
    print(f"Match con score > 0: {len(df[df['score'] > 0])}")
    print(f"Categorie trovate: {len(category_counts)}")
    print(f"Files generati:")
    print(f"  - statistics_folder_{folder_name}.png")
    print(f"  - summary_category_{folder_name}.csv")
    print(f"  - cross_analysis_{folder_name}.csv")

if __name__ == "__main__":
    main()