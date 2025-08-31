import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import json
from datetime import datetime
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

class SingleFingerprintAnalyzer:
    def __init__(self, target_fingerprint_id, base_dirs=None):
        """
        Analizza i match di una singola impronta contro tutte le altre
        
        Args:
            target_fingerprint_id (str): ID dell'impronta da analizzare (es. "01_Ay_03_01")
            base_dirs (list): Lista delle directory da analizzare
        """
        self.target_id = target_fingerprint_id
        
        if base_dirs is None:
            self.base_dirs = [f"/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/{i}" for i in range(25)]
        else:
            self.base_dirs = base_dirs
        
        self.output_dir = f"single_analysis_{target_fingerprint_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.data = []
        self.detailed_data = []
        self.target_matches = pd.DataFrame()
        
        print(f"Analyzing fingerprint: {self.target_id}")
        self.load_data()
        self.filter_target_matches()
    
    def load_data(self):
        """Carica tutti i dati CSV e JSON dal file system"""
        print("Loading data...")
        
        for base_dir in self.base_dirs:
            if not os.path.exists(base_dir):
                continue
                
            for root, dirs, files in os.walk(base_dir):
                csv_files = [f for f in files if f.endswith('.csv')]
                json_files = [f for f in files if f.endswith('.ndjson')]
                
                for csv_file in csv_files:
                    csv_path = os.path.join(root, csv_file)
                    try:
                        df = pd.read_csv(csv_path)
                        if not df.empty and len(df.columns) >= 6:
                            df['source_dir'] = base_dir
                            df['run_folder'] = os.path.basename(root)
                            self.data.append(df)
                    except Exception as e:
                        print(f"Error loading {csv_path}: {e}")
                
                for json_file in json_files:
                    json_path = os.path.join(root, json_file)
                    try:
                        with open(json_path, 'r') as f:
                            for line in f:
                                if line.strip():
                                    detail = json.loads(line.strip())
                                    detail['source_dir'] = base_dir
                                    detail['run_folder'] = os.path.basename(root)
                                    self.detailed_data.append(detail)
                    except Exception as e:
                        print(f"Error loading {json_path}: {e}")
        
        if self.data:
            self.df = pd.concat(self.data, ignore_index=True)
            self.df = self.df[self.df['relation'] != 'unknown']
        else:
            self.df = pd.DataFrame()
        
        print(f"Loaded {len(self.df)} total records")
    
    def filter_target_matches(self):
        """Filtra solo i match dell'impronta target come idA"""
        if self.df.empty:
            print("No data available")
            return
        
        # Filtra solo i record dove l'impronta target è idA
        self.target_matches = self.df[self.df['idA'] == self.target_id].copy()
        
        print(f"Found {len(self.target_matches)} comparisons for {self.target_id}")
        
        if self.target_matches.empty:
            print(f"No matches found for fingerprint {self.target_id}")
            return
        
        # Aggiungi classificazioni
        self.classify_relationships()
        
    def classify_relationships(self):
        """Classifica le relazioni in categorie"""
        # Mappa relazioni specifiche a categorie generiche
        family_mapping = {
            'same_individual': 'same_individual',
            'twins': 'family_related',
            'siblings': 'family_related', 
            'child_father': 'family_related',
            'different_individual': 'unrelated'
        }
        
        self.target_matches['relationship_category'] = self.target_matches['relation'].map(family_mapping).fillna('other')
        
        # Estrai informazioni dal pattern ID
        self.target_matches['target_pattern'] = self.target_matches['idA'].str.extract(r'(\d+_[A-Z][a-z0-9]+)_')[0]
        self.target_matches['compared_pattern'] = self.target_matches['idB'].str.extract(r'(\d+_[A-Z][a-z0-9]+)_')[0]
        
        # Determina se è stesso individuo basato su pattern
        self.target_matches['is_same_individual'] = (
            self.target_matches['target_pattern'] == self.target_matches['compared_pattern']
        )
    
    # ...existing code...

    def analyze_relationship_distribution(self):
        """Analizza la distribuzione delle relazioni per l'impronta target"""
        if self.target_matches.empty:
            return
        
        print("Analyzing relationship distribution...")
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # 1. Distribuzione per categoria generica (basata su confronti, come prima)
        ax1 = axes[0, 0]
        category_counts = self.target_matches['relationship_category'].value_counts()
        category_percentages = (category_counts / len(self.target_matches)) * 100
        
        bars1 = ax1.bar(category_percentages.index, category_percentages.values)
        ax1.set_title(f'Relationship Categories for {self.target_id} (by comparisons)')
        ax1.set_ylabel('Percentage (%)')
        ax1.tick_params(axis='x', rotation=45)
        
        # Aggiungi percentuali sopra le barre
        for bar, pct in zip(bars1, category_percentages.values):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                    f'{pct:.1f}%', ha='center', va='bottom')
        
        # 2. Distribuzione per categoria generica (basata su impronte uniche)
        ax2 = axes[0, 1]
        unique_by_category = self.target_matches.groupby('relationship_category')['idB'].nunique()
        unique_percentages = (unique_by_category / unique_by_category.sum()) * 100
        
        bars2 = ax2.bar(unique_percentages.index, unique_percentages.values)
        ax2.set_title(f'Relationship Categories for {self.target_id} (by unique fingerprints)')
        ax2.set_ylabel('Percentage (%)')
        ax2.tick_params(axis='x', rotation=45)
        
        # Aggiungi percentuali sopra le barre
        for bar, pct in zip(bars2, unique_percentages.values):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                    f'{pct:.1f}%', ha='center', va='bottom')
        
        # 3. Success rate per categoria (rimane basato su confronti, ma puoi modificarlo se vuoi)
        ax3 = axes[1, 0]
        success_by_category = self.target_matches.groupby('relationship_category').agg({
            'score': ['count', lambda x: (x.notna()).sum()]
        }).round(2)
        success_by_category.columns = ['total', 'successful']
        success_by_category['success_rate'] = (success_by_category['successful'] / success_by_category['total']) * 100
        
        bars3 = ax3.bar(success_by_category.index, success_by_category['success_rate'])
        ax3.set_title(f'Success Rate by Category for {self.target_id}')
        ax3.set_ylabel('Success Rate (%)')
        ax3.tick_params(axis='x', rotation=45)
        
        # Aggiungi percentuali e conteggi
        for i, (bar, rate, total, success) in enumerate(zip(bars3, success_by_category['success_rate'], 
                                                        success_by_category['total'], success_by_category['successful'])):
            ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                    f'{rate:.1f}%\n({success}/{total})', ha='center', va='bottom')
        
        # 4. Score distribution per categoria (rimane invariato)
        ax4 = axes[1, 1]
        categories = self.target_matches['relationship_category'].unique()
        
        for category in categories:
            scores = self.target_matches[self.target_matches['relationship_category'] == category]['score'].dropna()
            if len(scores) > 0:
                ax4.hist(scores, alpha=0.6, label=f'{category} (n={len(scores)})', bins=20)
        
        ax4.set_xlabel('Score')
        ax4.set_ylabel('Frequency')
        ax4.set_title(f'Score Distribution by Category for {self.target_id}')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'relationship_distribution.png'), dpi=300, bbox_inches='tight')
        plt.close()

# ...existing code...
        """Analizza la distribuzione delle relazioni per l'impronta target"""
        if self.target_matches.empty:
            return
        
        print("Analyzing relationship distribution...")
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # 1. Distribuzione per categoria generica
        ax1 = axes[0, 0]
        category_counts = self.target_matches['relationship_category'].value_counts()
        category_percentages = (category_counts / len(self.target_matches)) * 100
        
        bars1 = ax1.bar(category_percentages.index, category_percentages.values)
        ax1.set_title(f'Relationship Categories for {self.target_id}')
        ax1.set_ylabel('Percentage (%)')
        ax1.tick_params(axis='x', rotation=45)
        
        # Aggiungi percentuali sopra le barre
        for bar, pct in zip(bars1, category_percentages.values):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                    f'{pct:.1f}%', ha='center', va='bottom')
        
        # 2. Distribuzione per relazione specifica
        ax2 = axes[0, 1]
        relation_counts = self.target_matches['relation'].value_counts()
        relation_percentages = (relation_counts / len(self.target_matches)) * 100
        
        bars2 = ax2.bar(relation_percentages.index, relation_percentages.values)
        ax2.set_title(f'Specific Relations for {self.target_id}')
        ax2.set_ylabel('Percentage (%)')
        ax2.tick_params(axis='x', rotation=45)
        
        # Aggiungi percentuali sopra le barre
        for bar, pct in zip(bars2, relation_percentages.values):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                    f'{pct:.1f}%', ha='center', va='bottom')
        
        # 3. Success rate per categoria
        ax3 = axes[1, 0]
        success_by_category = self.target_matches.groupby('relationship_category').agg({
            'score': ['count', lambda x: (x.notna()).sum()]
        }).round(2)
        success_by_category.columns = ['total', 'successful']
        success_by_category['success_rate'] = (success_by_category['successful'] / success_by_category['total']) * 100
        
        bars3 = ax3.bar(success_by_category.index, success_by_category['success_rate'])
        ax3.set_title(f'Success Rate by Category for {self.target_id}')
        ax3.set_ylabel('Success Rate (%)')
        ax3.tick_params(axis='x', rotation=45)
        
        # Aggiungi percentuali e conteggi
        for i, (bar, rate, total, success) in enumerate(zip(bars3, success_by_category['success_rate'], 
                                                           success_by_category['total'], success_by_category['successful'])):
            ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                    f'{rate:.1f}%\n({success}/{total})', ha='center', va='bottom')
        
        # 4. Score distribution per categoria
        ax4 = axes[1, 1]
        categories = self.target_matches['relationship_category'].unique()
        
        for category in categories:
            scores = self.target_matches[self.target_matches['relationship_category'] == category]['score'].dropna()
            if len(scores) > 0:
                ax4.hist(scores, alpha=0.6, label=f'{category} (n={len(scores)})', bins=20)
        
        ax4.set_xlabel('Score')
        ax4.set_ylabel('Frequency')
        ax4.set_title(f'Score Distribution by Category for {self.target_id}')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'relationship_distribution.png'), dpi=300, bbox_inches='tight')
        plt.close()
    
    def analyze_match_quality(self):
        """Analizza la qualità dei match per l'impronta target"""
        if self.target_matches.empty:
            return
        
        print("Analyzing match quality...")
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        
        # 1. Score vs Nodes Mapped
        ax1 = axes[0, 0]
        categories = self.target_matches['relationship_category'].unique()
        colors = plt.cm.Set1(np.linspace(0, 1, len(categories)))
        
        for category, color in zip(categories, colors):
            cat_data = self.target_matches[self.target_matches['relationship_category'] == category]
            if not cat_data.empty:
                ax1.scatter(cat_data['nodes_mapped'], cat_data['score'], 
                          alpha=0.7, label=category, c=[color], s=50)
        
        ax1.set_xlabel('Nodes Mapped')
        ax1.set_ylabel('Score')
        ax1.set_title(f'Score vs Nodes Mapped for {self.target_id}')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. Box plot degli score per relazione
        ax2 = axes[0, 1]
        score_data = []
        labels = []
        for relation in self.target_matches['relation'].unique():
            scores = self.target_matches[self.target_matches['relation'] == relation]['score'].dropna()
            if len(scores) > 0:
                score_data.append(scores)
                labels.append(f'{relation}\n(n={len(scores)})')
        
        if score_data:
            bp = ax2.boxplot(score_data, labels=labels, patch_artist=True)
            for patch, color in zip(bp['boxes'], colors):
                patch.set_facecolor(color)
            ax2.set_ylabel('Score')
            ax2.set_title(f'Score Distribution by Relation for {self.target_id}')
            ax2.tick_params(axis='x', rotation=45)
            ax2.grid(True, alpha=0.3)
        
        # 3. Quality bins
        ax3 = axes[0, 2]
        valid_scores = self.target_matches['score'].dropna()
        if not valid_scores.empty:
            score_bins = pd.cut(valid_scores, 
                               bins=[0, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0], 
                               labels=['Very Low\n(0-0.3)', 'Low\n(0.3-0.5)', 'Medium\n(0.5-0.7)', 
                                      'Good\n(0.7-0.8)', 'High\n(0.8-0.9)', 'Excellent\n(0.9-1.0)'])
            quality_dist = score_bins.value_counts()
            
            wedges, texts, autotexts = ax3.pie(quality_dist.values, labels=quality_dist.index, 
                                              autopct='%1.1f%%', startangle=90)
            ax3.set_title(f'Match Quality Distribution for {self.target_id}')
        
        # 4. Nodes mapped distribution
        ax4 = axes[1, 0]
        for category in categories:
            nodes = self.target_matches[self.target_matches['relationship_category'] == category]['nodes_mapped'].dropna()
            if len(nodes) > 0:
                ax4.hist(nodes, alpha=0.6, label=f'{category} (n={len(nodes)})', 
                        bins=range(3, 15), align='left')
        
        ax4.set_xlabel('Nodes Mapped')
        ax4.set_ylabel('Frequency')
        ax4.set_title(f'Nodes Mapped Distribution for {self.target_id}')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        # 5. Performance by individual pattern
        ax5 = axes[1, 1]
        pattern_stats = self.target_matches.groupby('compared_pattern').agg({
            'score': ['mean', 'count', 'std']
        }).round(3)
        pattern_stats.columns = ['avg_score', 'count', 'std_score']
        pattern_stats = pattern_stats[pattern_stats['count'] >= 2]  # Solo pattern con almeno 2 confronti
        
        if not pattern_stats.empty:
            top_patterns = pattern_stats.nlargest(10, 'count')
            bars = ax5.bar(range(len(top_patterns)), top_patterns['avg_score'], 
                          yerr=top_patterns['std_score'], capsize=5)
            ax5.set_xticks(range(len(top_patterns)))
            ax5.set_xticklabels(top_patterns.index, rotation=45, ha='right')
            ax5.set_ylabel('Average Score')
            ax5.set_title(f'Performance vs Top Individual Patterns for {self.target_id}')
            ax5.grid(True, alpha=0.3)
            
            # Aggiungi conteggi sopra le barre
            for bar, count in zip(bars, top_patterns['count']):
                ax5.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, 
                        f'n={count}', ha='center', va='bottom', fontsize=8)
        
        # 6. Statistics table
        ax6 = axes[1, 2]
        stats_data = []
        for category in self.target_matches['relationship_category'].unique():
            cat_data = self.target_matches[self.target_matches['relationship_category'] == category]
            stats_data.append([
                category,
                len(cat_data),
                len(cat_data[cat_data['score'].notna()]),
                f"{(len(cat_data[cat_data['score'].notna()])/len(cat_data)*100):.1f}%",
                f"{cat_data['score'].mean():.3f}" if not cat_data['score'].empty else "N/A",
                f"{cat_data['nodes_mapped'].mean():.1f}" if not cat_data['nodes_mapped'].empty else "N/A"
            ])
        
        stats_df = pd.DataFrame(stats_data, 
                               columns=['Category', 'Total', 'Matched', 'Success%', 'Avg Score', 'Avg Nodes'])
        
        table = ax6.table(cellText=stats_df.values,
                         colLabels=stats_df.columns,
                         cellLoc='center',
                         loc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.5)
        ax6.axis('off')
        ax6.set_title(f'Summary Statistics for {self.target_id}')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'match_quality_analysis.png'), dpi=300, bbox_inches='tight')
        plt.close()
    
    def create_detailed_report(self):
        """Crea un report dettagliato per l'impronta target"""
        if self.target_matches.empty:
            return {}
        
        print("Creating detailed report...")
        
        # Statistiche generali
        total_comparisons = len(self.target_matches)
        successful_matches = len(self.target_matches[self.target_matches['score'].notna()])
        success_rate = (successful_matches / total_comparisons) * 100 if total_comparisons > 0 else 0
        
        # Statistiche per categoria
        category_stats = {}
        for category in self.target_matches['relationship_category'].unique():
            cat_data = self.target_matches[self.target_matches['relationship_category'] == category]
            category_stats[category] = {
                'total_comparisons': len(cat_data),
                'successful_matches': len(cat_data[cat_data['score'].notna()]),
                'success_rate': (len(cat_data[cat_data['score'].notna()]) / len(cat_data)) * 100 if len(cat_data) > 0 else 0,
                'avg_score': float(cat_data['score'].mean()) if not cat_data['score'].empty else None,
                'std_score': float(cat_data['score'].std()) if not cat_data['score'].empty else None,
                'avg_nodes': float(cat_data['nodes_mapped'].mean()) if not cat_data['nodes_mapped'].empty else None,
                'percentage_of_total': (len(cat_data) / total_comparisons) * 100
            }
        
        # Statistiche per relazione specifica
        relation_stats = {}
        for relation in self.target_matches['relation'].unique():
            rel_data = self.target_matches[self.target_matches['relation'] == relation]
            relation_stats[relation] = {
                'total_comparisons': len(rel_data),
                'successful_matches': len(rel_data[rel_data['score'].notna()]),
                'success_rate': (len(rel_data[rel_data['score'].notna()]) / len(rel_data)) * 100 if len(rel_data) > 0 else 0,
                'avg_score': float(rel_data['score'].mean()) if not rel_data['score'].empty else None,
                'percentage_of_total': (len(rel_data) / total_comparisons) * 100
            }
        
        # Top matches
        top_matches = self.target_matches.nlargest(10, 'score')[['idB', 'relation', 'score', 'nodes_mapped']].to_dict('records')
        
        report = {
            'analysis_date': datetime.now().isoformat(),
            'target_fingerprint': self.target_id,
            'total_comparisons': total_comparisons,
            'successful_matches': successful_matches,
            'overall_success_rate': success_rate,
            'avg_score': float(self.target_matches['score'].mean()) if not self.target_matches['score'].empty else None,
            'std_score': float(self.target_matches['score'].std()) if not self.target_matches['score'].empty else None,
            'avg_nodes_mapped': float(self.target_matches['nodes_mapped'].mean()) if not self.target_matches['nodes_mapped'].empty else None,
            'unique_compared_fingerprints': len(self.target_matches['idB'].unique()),
            'category_statistics': category_stats,
            'relation_statistics': relation_stats,
            'top_10_matches': top_matches
        }
        
        # Salva il report
        with open(os.path.join(self.output_dir, 'detailed_report.json'), 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Salva i dati filtrati
        self.target_matches.to_csv(os.path.join(self.output_dir, 'target_matches.csv'), index=False)
        
        return report
    
    def run_complete_analysis(self):
        """Esegue l'analisi completa per l'impronta target"""
        if self.target_matches.empty:
            print(f"No data found for fingerprint {self.target_id}")
            return None
        
        print(f"Starting complete analysis for {self.target_id}...")
        
        # Esegui tutte le analisi
        self.analyze_relationship_distribution()
        self.analyze_match_quality()
        report = self.create_detailed_report()
        
        # Stampa summary
        print(f"\n=== ANALYSIS SUMMARY FOR {self.target_id} ===")
        print(f"Total comparisons: {report['total_comparisons']:,}")
        print(f"Successful matches: {report['successful_matches']:,}")
        print(f"Overall success rate: {report['overall_success_rate']:.1f}%")
        
        if report['avg_score'] is not None:
            print(f"Average score: {report['avg_score']:.3f} ± {report['std_score']:.3f}")
        
        print(f"Average nodes mapped: {report['avg_nodes_mapped']:.1f}")
        print(f"Unique compared fingerprints: {report['unique_compared_fingerprints']}")
        
        print("\nBREAKDOWN BY CATEGORY:")
        for category, stats in report['category_statistics'].items():
            print(f"  {category}: {stats['total_comparisons']} comparisons, "
                  f"{stats['success_rate']:.1f}% success rate, "
                  f"{stats['percentage_of_total']:.1f}% of total")
        
        print(f"\nResults saved in: {self.output_dir}")
        return report

if __name__ == "__main__":
    # MODIFICA QUESTA VARIABILE PER CAMBIARE L'IMPRONTA DA ANALIZZARE
    TARGET_FINGERPRINT = "01_Ay_03_01"
    
    # Inizializza l'analyzer
    analyzer = SingleFingerprintAnalyzer(TARGET_FINGERPRINT)
    
    # Esegui l'analisi completa
    analyzer.run_complete_analysis()