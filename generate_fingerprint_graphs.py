#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
from matplotlib.patches import Rectangle
import warnings
warnings.filterwarnings('ignore')

def setup_plotting_style():
    """Configura lo stile dei grafici"""
    plt.style.use('default')
    sns.set_palette("husl")
    plt.rcParams['figure.figsize'] = (12, 8)
    plt.rcParams['font.size'] = 10
    plt.rcParams['axes.titlesize'] = 14
    plt.rcParams['axes.labelsize'] = 12
    plt.rcParams['xtick.labelsize'] = 10
    plt.rcParams['ytick.labelsize'] = 10
    plt.rcParams['legend.fontsize'] = 10

def load_data(csv_file):
    """Carica i dati dal CSV"""
    df = pd.read_csv(csv_file)
    print(f"Dataset caricato: {len(df)} impronte, {df.columns.shape[0]} colonne")
    return df

def create_output_directory(base_path):
    """Crea la directory di output per i grafici"""
    output_dir = os.path.join(base_path, "fingerprint_analysis_graphs")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def save_plot(fig, output_dir, filename, dpi=300):
    """Salva il grafico in formato PNG e CSV se applicabile"""
    png_path = os.path.join(output_dir, f"{filename}.png")
    fig.savefig(png_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    print(f"Grafico salvato: {png_path}")
    plt.close(fig)

def plot_overall_performance(df, output_dir):
    """1. Grafici delle performance generali"""
    
    # 1.1 Distribuzione dei match rates
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Istogramma dei match rates
    ax1.hist(df['overall_match_rate'], bins=20, alpha=0.7, color='skyblue', edgecolor='black')
    ax1.set_xlabel('Overall Match Rate')
    ax1.set_ylabel('Number of Fingerprints')
    ax1.set_title('Distribution of Overall Match Rates')
    ax1.grid(True, alpha=0.3)
    
    # Box plot dei match rates
    ax2.boxplot(df['overall_match_rate'], vert=True)
    ax2.set_ylabel('Overall Match Rate')
    ax2.set_title('Overall Match Rate Distribution')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    save_plot(fig, output_dir, "01_overall_performance_distribution")
    
    # Salva i dati CSV per questo grafico
    summary_data = pd.DataFrame({
        'metric': ['mean', 'median', 'std', 'min', 'max', 'q25', 'q75'],
        'overall_match_rate': [
            df['overall_match_rate'].mean(),
            df['overall_match_rate'].median(), 
            df['overall_match_rate'].std(),
            df['overall_match_rate'].min(),
            df['overall_match_rate'].max(),
            df['overall_match_rate'].quantile(0.25),
            df['overall_match_rate'].quantile(0.75)
        ]
    })
    summary_data.to_csv(os.path.join(output_dir, "01_overall_performance_distribution.csv"), index=False)
    
    # 1.2 Scatter plot: Match Rate vs Average Score
    fig, ax = plt.subplots(figsize=(12, 8))
    scatter = ax.scatter(df['overall_match_rate'], df['overall_avg_score'], 
                        alpha=0.6, s=60, c=df['total_comparisons'], 
                        cmap='viridis')
    ax.set_xlabel('Overall Match Rate')
    ax.set_ylabel('Overall Average Score')
    ax.set_title('Match Rate vs Average Score (colored by total comparisons)')
    plt.colorbar(scatter, label='Total Comparisons')
    ax.grid(True, alpha=0.3)
    
    save_plot(fig, output_dir, "02_match_rate_vs_score")
    
    # CSV per scatter plot
    scatter_data = df[['fingerprint_code', 'overall_match_rate', 'overall_avg_score', 'total_comparisons']].copy()
    scatter_data.to_csv(os.path.join(output_dir, "02_match_rate_vs_score.csv"), index=False)

def plot_category_analysis(df, output_dir):
    """2. Analisi per categoria di impronte"""
    
    categories = ['01_Ay', '01_G1', '01_G2', '02_Ax', '02_B0']
    
    # 2.1 Match rates per categoria
    category_data = []
    for cat in categories:
        col_comparisons = f'{cat}_comparisons'
        col_matches = f'{cat}_matches'
        col_avg_score = f'{cat}_avg_score'
        
        if col_comparisons in df.columns:
            # Calcola le statistiche aggregate per categoria
            total_comparisons = df[col_comparisons].sum()
            total_matches = df[col_matches].sum()
            avg_match_rate = total_matches / max(total_comparisons, 1)
            avg_score = df[df[col_comparisons] > 0][col_avg_score].mean()
            
            category_data.append({
                'category': cat,
                'total_comparisons': total_comparisons,
                'total_matches': total_matches,
                'match_rate': avg_match_rate,
                'avg_score': avg_score if not pd.isna(avg_score) else 0
            })
    
    cat_df = pd.DataFrame(category_data)
    
    # Grafico a barre delle match rates per categoria
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    bars1 = ax1.bar(cat_df['category'], cat_df['match_rate'], color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7'])
    ax1.set_xlabel('Fingerprint Category')
    ax1.set_ylabel('Match Rate')
    ax1.set_title('Match Rate by Fingerprint Category')
    ax1.set_ylim(0, 1)
    plt.setp(ax1.get_xticklabels(), rotation=45)
    
    # Aggiungi valori sulle barre
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                f'{height:.3f}', ha='center', va='bottom')
    
    # Average scores per categoria
    bars2 = ax2.bar(cat_df['category'], cat_df['avg_score'], color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7'])
    ax2.set_xlabel('Fingerprint Category')
    ax2.set_ylabel('Average Score')
    ax2.set_title('Average Score by Fingerprint Category')
    plt.setp(ax2.get_xticklabels(), rotation=45)
    
    # Aggiungi valori sulle barre
    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                f'{height:.3f}', ha='center', va='bottom')
    
    plt.tight_layout()
    save_plot(fig, output_dir, "03_category_performance")
    
    # Salva CSV
    cat_df.to_csv(os.path.join(output_dir, "03_category_performance.csv"), index=False)
    
    # 2.2 Heatmap delle performance per categoria
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Crea matrice per heatmap
    heatmap_data = []
    for cat in categories:
        col_comparisons = f'{cat}_comparisons'
        col_matches = f'{cat}_matches'
        col_match_rate = f'{cat}_match_rate'
        col_avg_score = f'{cat}_avg_score'
        
        if col_comparisons in df.columns:
            cat_data = df[df[col_comparisons] > 0][[col_match_rate, col_avg_score]].mean()
            heatmap_data.append([cat_data[col_match_rate], cat_data[col_avg_score]])
        else:
            heatmap_data.append([0, 0])
    
    heatmap_df = pd.DataFrame(heatmap_data, 
                             index=categories, 
                             columns=['Match Rate', 'Avg Score'])
    
    sns.heatmap(heatmap_df, annot=True, fmt='.3f', cmap='RdYlGn', ax=ax)
    ax.set_title('Performance Heatmap by Category')
    
    save_plot(fig, output_dir, "04_category_heatmap")
    heatmap_df.to_csv(os.path.join(output_dir, "04_category_heatmap.csv"))

def plot_relation_analysis(df, output_dir):
    """3. Analisi per tipo di relazione"""
    
    relations = ['same_individual', 'siblings', 'stranger', 'same_family', 'child_father', 'twins']
    
    # 3.1 Performance per tipo di relazione
    relation_data = []
    for rel in relations:
        col_comparisons = f'{rel}_comparisons'
        col_matches = f'{rel}_matches'
        col_avg_score = f'{rel}_avg_score'
        
        if col_comparisons in df.columns:
            total_comparisons = df[col_comparisons].sum()
            total_matches = df[col_matches].sum()
            avg_match_rate = total_matches / max(total_comparisons, 1)
            avg_score = df[df[col_comparisons] > 0][col_avg_score].mean()
            
            relation_data.append({
                'relation': rel,
                'total_comparisons': total_comparisons,
                'total_matches': total_matches,
                'match_rate': avg_match_rate,
                'avg_score': avg_score if not pd.isna(avg_score) else 0
            })
    
    rel_df = pd.DataFrame(relation_data)
    rel_df = rel_df[rel_df['total_comparisons'] > 0]  # Filtra relazioni senza dati
    
    # Grafico a barre orizzontali
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Match rates
    bars1 = ax1.barh(rel_df['relation'], rel_df['match_rate'], 
                     color=plt.cm.Set3(np.linspace(0, 1, len(rel_df))))
    ax1.set_xlabel('Match Rate')
    ax1.set_title('Match Rate by Relation Type')
    ax1.set_xlim(0, 1)
    
    # Aggiungi valori
    for i, bar in enumerate(bars1):
        width = bar.get_width()
        ax1.text(width + 0.01, bar.get_y() + bar.get_height()/2.,
                f'{width:.3f}', ha='left', va='center')
    
    # Average scores
    bars2 = ax2.barh(rel_df['relation'], rel_df['avg_score'],
                     color=plt.cm.Set3(np.linspace(0, 1, len(rel_df))))
    ax2.set_xlabel('Average Score')
    ax2.set_title('Average Score by Relation Type')
    
    # Aggiungi valori
    for i, bar in enumerate(bars2):
        width = bar.get_width()
        ax2.text(width + 0.01, bar.get_y() + bar.get_height()/2.,
                f'{width:.3f}', ha='left', va='center')
    
    plt.tight_layout()
    save_plot(fig, output_dir, "05_relation_performance")
    
    # Salva CSV
    rel_df.to_csv(os.path.join(output_dir, "05_relation_performance.csv"), index=False)

def plot_top_bottom_performers(df, output_dir):
    """4. Top e bottom performers"""
    
    # 4.1 Top 10 e Bottom 10 per match rate
    df_sorted = df.sort_values('overall_match_rate', ascending=False)
    top_10 = df_sorted.head(10)
    bottom_10 = df_sorted.tail(10)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))
    
    # Top 10
    bars1 = ax1.bar(range(len(top_10)), top_10['overall_match_rate'], color='green', alpha=0.7)
    ax1.set_xlabel('Fingerprint')
    ax1.set_ylabel('Match Rate')
    ax1.set_title('Top 10 Fingerprints by Match Rate')
    ax1.set_xticks(range(len(top_10)))
    ax1.set_xticklabels(top_10['fingerprint_code'], rotation=45, ha='right')
    
    # Aggiungi valori
    for i, bar in enumerate(bars1):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                f'{height:.3f}', ha='center', va='bottom', fontsize=8)
    
    # Bottom 10
    bars2 = ax2.bar(range(len(bottom_10)), bottom_10['overall_match_rate'], color='red', alpha=0.7)
    ax2.set_xlabel('Fingerprint')
    ax2.set_ylabel('Match Rate')
    ax2.set_title('Bottom 10 Fingerprints by Match Rate')
    ax2.set_xticks(range(len(bottom_10)))
    ax2.set_xticklabels(bottom_10['fingerprint_code'], rotation=45, ha='right')
    
    # Aggiungi valori
    for i, bar in enumerate(bars2):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                f'{height:.3f}', ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    save_plot(fig, output_dir, "06_top_bottom_performers")
    
    # Salva CSV
    top_bottom_df = pd.concat([
        top_10[['fingerprint_code', 'overall_match_rate']].assign(category='top_10'),
        bottom_10[['fingerprint_code', 'overall_match_rate']].assign(category='bottom_10')
    ])
    top_bottom_df.to_csv(os.path.join(output_dir, "06_top_bottom_performers.csv"), index=False)

def plot_comparison_volume_analysis(df, output_dir):
    """5. Analisi del volume di confronti"""
    
    # 5.1 Distribuzione del numero di confronti
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    
    # Istogramma confronti totali
    ax1.hist(df['total_comparisons'], bins=20, alpha=0.7, color='lightblue', edgecolor='black')
    ax1.set_xlabel('Total Comparisons')
    ax1.set_ylabel('Number of Fingerprints')
    ax1.set_title('Distribution of Total Comparisons')
    ax1.grid(True, alpha=0.3)
    
    # Istogramma match totali
    ax2.hist(df['total_matches'], bins=20, alpha=0.7, color='lightgreen', edgecolor='black')
    ax2.set_xlabel('Total Matches')
    ax2.set_ylabel('Number of Fingerprints')
    ax2.set_title('Distribution of Total Matches')
    ax2.grid(True, alpha=0.3)
    
    # Scatter: Comparisons vs Matches
    ax3.scatter(df['total_comparisons'], df['total_matches'], alpha=0.6)
    ax3.set_xlabel('Total Comparisons')
    ax3.set_ylabel('Total Matches')
    ax3.set_title('Total Comparisons vs Total Matches')
    ax3.grid(True, alpha=0.3)
    
    # Box plot per categorie
    categories = ['01_Ay', '01_G1', '01_G2', '02_Ax', '02_B0']
    category_comparisons = []
    category_labels = []
    
    for cat in categories:
        col_comparisons = f'{cat}_comparisons'
        if col_comparisons in df.columns:
            cat_data = df[df[col_comparisons] > 0][col_comparisons]
            if len(cat_data) > 0:
                category_comparisons.append(cat_data)
                category_labels.append(cat)
    
    if category_comparisons:
        ax4.boxplot(category_comparisons, labels=category_labels)
        ax4.set_xlabel('Category')
        ax4.set_ylabel('Comparisons')
        ax4.set_title('Comparisons Distribution by Category')
        plt.setp(ax4.get_xticklabels(), rotation=45)
        ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    save_plot(fig, output_dir, "07_comparison_volume_analysis")
    
    # Salva dati di volume
    volume_data = df[['fingerprint_code', 'total_comparisons', 'total_matches']].copy()
    volume_data['match_efficiency'] = volume_data['total_matches'] / volume_data['total_comparisons']
    volume_data.to_csv(os.path.join(output_dir, "07_comparison_volume_analysis.csv"), index=False)

def plot_correlation_matrix(df, output_dir):
    """6. Matrice di correlazione"""
    
    # Seleziona solo le colonne numeriche principali
    numeric_cols = ['total_comparisons', 'total_matches', 'overall_match_rate', 'overall_avg_score']
    
    # Aggiungi colonne delle categorie se esistono
    categories = ['01_Ay', '01_G1', '01_G2', '02_Ax', '02_B0']
    for cat in categories:
        match_rate_col = f'{cat}_match_rate'
        avg_score_col = f'{cat}_avg_score'
        if match_rate_col in df.columns:
            numeric_cols.extend([match_rate_col, avg_score_col])
    
    # Filtra le colonne che esistono realmente
    available_cols = [col for col in numeric_cols if col in df.columns]
    correlation_data = df[available_cols].fillna(0)
    
    # Calcola la matrice di correlazione
    correlation_matrix = correlation_data.corr()
    
    # Crea il grafico
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(correlation_matrix, annot=True, fmt='.2f', cmap='coolwarm', 
                center=0, square=True, ax=ax)
    ax.set_title('Correlation Matrix of Performance Metrics')
    
    save_plot(fig, output_dir, "08_correlation_matrix")
    correlation_matrix.to_csv(os.path.join(output_dir, "08_correlation_matrix.csv"))

def generate_summary_report(df, output_dir):
    """7. Genera un report riassuntivo"""
    
    report = {
        'total_fingerprints': len(df),
        'total_comparisons_all': df['total_comparisons'].sum(),
        'total_matches_all': df['total_matches'].sum(),
        'global_match_rate': df['total_matches'].sum() / df['total_comparisons'].sum(),
        'avg_match_rate': df['overall_match_rate'].mean(),
        'avg_score': df['overall_avg_score'].mean(),
        'best_fingerprint': df.loc[df['overall_match_rate'].idxmax(), 'fingerprint_code'],
        'best_match_rate': df['overall_match_rate'].max(),
        'worst_fingerprint': df.loc[df['overall_match_rate'].idxmin(), 'fingerprint_code'],
        'worst_match_rate': df['overall_match_rate'].min(),
    }
    
    # Converti in DataFrame e salva
    report_df = pd.DataFrame([report])
    report_df.to_csv(os.path.join(output_dir, "09_summary_report.csv"), index=False)
    
    # Crea anche un grafico riassuntivo
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    
    # Grafico a torta per distribuzione categorie
    categories = ['01_Ay', '01_G1', '01_G2', '02_Ax', '02_B0']
    category_counts = []
    category_labels = []
    
    for cat in categories:
        col_comparisons = f'{cat}_comparisons'
        if col_comparisons in df.columns:
            count = (df[col_comparisons] > 0).sum()
            if count > 0:
                category_counts.append(count)
                category_labels.append(cat)
    
    ax1.pie(category_counts, labels=category_labels, autopct='%1.1f%%', startangle=90)
    ax1.set_title('Distribution of Fingerprints by Category')
    
    # Match rate distribution
    ax2.hist(df['overall_match_rate'], bins=15, alpha=0.7, color='skyblue', edgecolor='black')
    ax2.axvline(df['overall_match_rate'].mean(), color='red', linestyle='--', 
                label=f'Mean: {df["overall_match_rate"].mean():.3f}')
    ax2.set_xlabel('Match Rate')
    ax2.set_ylabel('Frequency')
    ax2.set_title('Overall Match Rate Distribution')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Top 5 e Bottom 5
    df_sorted = df.sort_values('overall_match_rate', ascending=False)
    top_5 = df_sorted.head(5)
    bottom_5 = df_sorted.tail(5).iloc[::-1]  # Inverte per ordine crescente
    
    # Combina top e bottom
    combined = pd.concat([top_5, bottom_5])
    colors = ['green'] * 5 + ['red'] * 5
    
    bars = ax3.barh(range(len(combined)), combined['overall_match_rate'], color=colors, alpha=0.7)
    ax3.set_yticks(range(len(combined)))
    ax3.set_yticklabels(combined['fingerprint_code'], fontsize=8)
    ax3.set_xlabel('Match Rate')
    ax3.set_title('Top 5 (Green) and Bottom 5 (Red) Performers')
    ax3.grid(True, alpha=0.3)
    
    # Statistiche generali (tabella)
    stats_data = [
        ['Total Fingerprints', f"{len(df)}"],
        ['Total Comparisons', f"{df['total_comparisons'].sum():,}"],
        ['Total Matches', f"{df['total_matches'].sum():,}"],
        ['Global Match Rate', f"{report['global_match_rate']:.3f}"],
        ['Average Match Rate', f"{report['avg_match_rate']:.3f}"],
        ['Average Score', f"{report['avg_score']:.3f}"]
    ]
    
    ax4.axis('tight')
    ax4.axis('off')
    table = ax4.table(cellText=stats_data,
                     colLabels=['Metric', 'Value'],
                     cellLoc='left',
                     loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 2)
    ax4.set_title('Summary Statistics')
    
    plt.tight_layout()
    save_plot(fig, output_dir, "09_summary_dashboard")
    
    return report

def main():
    """Funzione principale"""
    csv_file = "/Users/riccardotortorelli/Desktop/Tesi/fingerprint_statistics.csv"
    base_path = "/Users/riccardotortorelli/Desktop/Tesi"
    
    print("=== FINGERPRINT ANALYSIS - GRAPH GENERATOR ===")
    print(f"Input CSV: {csv_file}")
    
    # Setup
    setup_plotting_style()
    
    # Carica dati
    df = load_data(csv_file)
    
    # Crea directory di output
    output_dir = create_output_directory(base_path)
    print(f"Output directory: {output_dir}")
    
    # Genera tutti i grafici
    print("\n1. Generating overall performance graphs...")
    plot_overall_performance(df, output_dir)
    
    print("\n2. Generating category analysis...")
    plot_category_analysis(df, output_dir)
    
    print("\n3. Generating relation analysis...")
    plot_relation_analysis(df, output_dir)
    
    print("\n4. Generating top/bottom performers...")
    plot_top_bottom_performers(df, output_dir)
    
    print("\n5. Generating comparison volume analysis...")
    plot_comparison_volume_analysis(df, output_dir)
    
    print("\n6. Generating correlation matrix...")
    plot_correlation_matrix(df, output_dir)
    
    print("\n7. Generating summary report...")
    summary = generate_summary_report(df, output_dir)
    
    print("\n=== GENERATION COMPLETE ===")
    print(f"Generated graphs in: {output_dir}")
    print(f"Total fingerprints analyzed: {summary['total_fingerprints']}")
    print(f"Global match rate: {summary['global_match_rate']:.3f}")
    print(f"Best performer: {summary['best_fingerprint']} ({summary['best_match_rate']:.3f})")
    print(f"Worst performer: {summary['worst_fingerprint']} ({summary['worst_match_rate']:.3f})")

if __name__ == "__main__":
    main()