import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import json
from datetime import datetime
import networkx as nx
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

class FingerprintAnalyzer:
    def __init__(self, base_dirs=None):
        if base_dirs is None:
            self.base_dirs = [f"/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/{i}" for i in range(59)]
        else:
            self.base_dirs = base_dirs
        
        self.output_dir = f"fingerprint_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.data = []
        self.detailed_data = []
        self.load_data()
    
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
        
        print(f"Loaded {len(self.df)} records and {len(self.detailed_data)} detailed records")
    
    def analyze_score_distributions(self):
        """Analizza la distribuzione degli score per tipo di relazione"""
        if self.df.empty:
            return
        
        print("Analyzing score distributions...")
        
        plt.figure(figsize=(15, 10))
        
        # Score distribution by relation type
        plt.subplot(2, 2, 1)
        relations = self.df['relation'].unique()
        for relation in relations:
            scores = self.df[self.df['relation'] == relation]['score'].dropna()
            if len(scores) > 0:
                plt.hist(scores, alpha=0.6, label=relation, bins=20)
        plt.xlabel('Score')
        plt.ylabel('Frequency')
        plt.title('Score Distribution by Relation Type')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Box plot of scores by relation
        plt.subplot(2, 2, 2)
        score_data = []
        labels = []
        for relation in relations:
            scores = self.df[self.df['relation'] == relation]['score'].dropna()
            if len(scores) > 0:
                score_data.append(scores)
                labels.append(relation)
        
        if score_data:
            plt.boxplot(score_data, labels=labels)
            plt.xticks(rotation=45)
            plt.ylabel('Score')
            plt.title('Score Distribution by Relation (Box Plot)')
            plt.grid(True, alpha=0.3)
        
        # Nodes mapped distribution
        plt.subplot(2, 2, 3)
        for relation in relations:
            nodes = self.df[self.df['relation'] == relation]['nodes_mapped'].dropna()
            if len(nodes) > 0:
                plt.hist(nodes, alpha=0.6, label=relation, bins=range(3, 15))
        plt.xlabel('Nodes Mapped')
        plt.ylabel('Frequency')
        plt.title('Nodes Mapped Distribution by Relation')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Score vs Nodes Mapped scatter
        plt.subplot(2, 2, 4)
        for relation in relations:
            rel_data = self.df[self.df['relation'] == relation]
            if not rel_data.empty:
                plt.scatter(rel_data['nodes_mapped'], rel_data['score'], 
                          alpha=0.6, label=relation, s=20)
        plt.xlabel('Nodes Mapped')
        plt.ylabel('Score')
        plt.title('Score vs Nodes Mapped')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'score_distributions.png'), dpi=300, bbox_inches='tight')
        plt.close()
    
    def analyze_family_relationships(self):
        """Analizza le relazioni familiari e crea network graph"""
        if self.df.empty:
            return
        
        print("Analyzing family relationships...")
        
        # Create family mapping
        family_mapping = {
            'same_individual': 'same_individual',
            'twins': 'family',
            'siblings': 'family', 
            'child_father': 'family',
            'different_individual': 'different_individual'
        }
        
        self.df['family_category'] = self.df['relation'].map(family_mapping).fillna('other')
        
        plt.figure(figsize=(15, 10))
        
        # Family relationship counts
        plt.subplot(2, 2, 1)
        family_counts = self.df['family_category'].value_counts()
        plt.pie(family_counts.values, labels=family_counts.index, autopct='%1.1f%%')
        plt.title('Distribution of Family Categories')
        
        # Average scores by family category
        plt.subplot(2, 2, 2)
        family_scores = self.df.groupby('family_category')['score'].agg(['mean', 'std'])
        plt.bar(family_scores.index, family_scores['mean'], 
                yerr=family_scores['std'], capsize=5)
        plt.ylabel('Average Score')
        plt.title('Average Scores by Family Category')
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)
        
        # Success rate by family category
        plt.subplot(2, 2, 3)
        success_rates = {}
        for category in self.df['family_category'].unique():
            cat_data = self.df[self.df['family_category'] == category]
            total_comparisons = len(cat_data)
            successful_matches = len(cat_data[cat_data['score'].notna()])
            success_rates[category] = (successful_matches / total_comparisons) * 100 if total_comparisons > 0 else 0
        
        plt.bar(success_rates.keys(), success_rates.values())
        plt.ylabel('Success Rate (%)')
        plt.title('Match Success Rate by Family Category')
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)
        
        # Create network graph
        plt.subplot(2, 2, 4)
        self.create_relationship_network()
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'family_relationships.png'), dpi=300, bbox_inches='tight')
        plt.close()
    
    def create_relationship_network(self):
        """Crea un network graph delle relazioni tra impronte"""
        G = nx.Graph()
        
        # Add nodes and edges based on relationships
        for _, row in self.df.iterrows():
            if pd.notna(row['score']) and row['score'] > 0.5:  # Only strong matches
                G.add_edge(row['idA'], row['idB'], 
                          weight=row['score'], 
                          relation=row['relation'])
        
        if len(G.nodes()) == 0:
            plt.text(0.5, 0.5, 'No strong relationships found\n(score > 0.5)', 
                    ha='center', va='center', transform=plt.gca().transAxes)
            return
        
        # Create layout
        pos = nx.spring_layout(G, k=1, iterations=50)
        
        # Color nodes by individual/family groups
        node_colors = []
        for node in G.nodes():
            # Extract individual ID pattern
            parts = node.split('_')
            if len(parts) >= 3:
                individual_id = f"{parts[0]}_{parts[1]}"
                if 'Ay' in individual_id:
                    node_colors.append('red')
                elif 'G1' in individual_id:
                    node_colors.append('blue')
                elif 'G2' in individual_id:
                    node_colors.append('green')
                elif 'Ax' in individual_id:
                    node_colors.append('orange')
                elif 'B0' in individual_id:
                    node_colors.append('purple')
                else:
                    node_colors.append('gray')
            else:
                node_colors.append('gray')
        
        # Draw network
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, 
                              node_size=50, alpha=0.7)
        nx.draw_networkx_edges(G, pos, alpha=0.3, width=0.5)
        
        # Add labels for high-degree nodes only
        high_degree_nodes = [node for node, degree in G.degree() if degree > 2]
        labels = {node: node.split('_')[-2:] for node in high_degree_nodes}
        nx.draw_networkx_labels(G, pos, labels, font_size=8)
        
        plt.title(f'Relationship Network\n({len(G.nodes())} nodes, {len(G.edges())} edges)')
        plt.axis('off')
    
    def analyze_match_success_rates(self):
        """Analizza i tassi di successo dei match"""
        if self.df.empty:
            return
        
        print("Analyzing match success rates...")
        
        plt.figure(figsize=(15, 8))
        
        # Success rate by individual ID pattern
        plt.subplot(2, 3, 1)
        self.df['individual_pattern'] = self.df['idA'].str.extract(r'(\d+_[A-Z][a-z0-9]+)_')
        pattern_success = self.df.groupby('individual_pattern').agg({
            'score': ['count', lambda x: (x.notna()).sum()]
        }).round(2)
        pattern_success.columns = ['total', 'successful']
        pattern_success['success_rate'] = (pattern_success['successful'] / pattern_success['total']) * 100
        
        top_patterns = pattern_success.nlargest(10, 'total')
        plt.bar(range(len(top_patterns)), top_patterns['success_rate'])
        plt.xticks(range(len(top_patterns)), top_patterns.index, rotation=45)
        plt.ylabel('Success Rate (%)')
        plt.title('Success Rate by Individual Pattern')
        plt.grid(True, alpha=0.3)
        
        # Score threshold analysis
        plt.subplot(2, 3, 2)
        thresholds = np.arange(0.1, 1.0, 0.05)
        threshold_counts = []
        for threshold in thresholds:
            count = len(self.df[self.df['score'] >= threshold])
            threshold_counts.append(count)
        
        plt.plot(thresholds, threshold_counts, marker='o')
        plt.xlabel('Score Threshold')
        plt.ylabel('Number of Matches')
        plt.title('Matches Above Score Threshold')
        plt.grid(True, alpha=0.3)
        
        # Nodes mapped vs success correlation
        plt.subplot(2, 3, 3)
        nodes_success = self.df.groupby('nodes_mapped').agg({
            'score': ['mean', 'count']
        }).round(3)
        nodes_success.columns = ['avg_score', 'count']
        
        sizes = nodes_success['count'] * 10  # Scale point sizes
        plt.scatter(nodes_success.index, nodes_success['avg_score'], s=sizes, alpha=0.6)
        plt.xlabel('Nodes Mapped')
        plt.ylabel('Average Score')
        plt.title('Average Score vs Nodes Mapped\n(size = frequency)')
        plt.grid(True, alpha=0.3)
        
        # Time-based analysis (if run folders have timestamps)
        plt.subplot(2, 3, 4)
        try:
            self.df['timestamp'] = pd.to_datetime(self.df['run_folder'].str.extract(r'(\d{8}_\d{6})')[0], 
                                                 format='%Y%m%d_%H%M%S', errors='coerce')
            if self.df['timestamp'].notna().any():
                time_analysis = self.df.groupby(self.df['timestamp'].dt.hour)['score'].mean()
                plt.plot(time_analysis.index, time_analysis.values, marker='o')
                plt.xlabel('Hour of Day')
                plt.ylabel('Average Score')
                plt.title('Performance by Hour of Day')
                plt.grid(True, alpha=0.3)
            else:
                plt.text(0.5, 0.5, 'No timestamp data available', 
                        ha='center', va='center', transform=plt.gca().transAxes)
        except:
            plt.text(0.5, 0.5, 'Timestamp parsing failed', 
                    ha='center', va='center', transform=plt.gca().transAxes)
        
        # Quality distribution
        plt.subplot(2, 3, 5)
        score_bins = pd.cut(self.df['score'].dropna(), 
                           bins=[0, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0], 
                           labels=['Very Low', 'Low', 'Medium', 'Good', 'High', 'Excellent'])
        quality_dist = score_bins.value_counts()
        plt.pie(quality_dist.values, labels=quality_dist.index, autopct='%1.1f%%')
        plt.title('Match Quality Distribution')
        
        # Detailed statistics table
        plt.subplot(2, 3, 6)
        stats_data = []
        for relation in self.df['relation'].unique():
            rel_data = self.df[self.df['relation'] == relation]
            stats_data.append([
                relation,
                len(rel_data),
                rel_data['score'].mean() if not rel_data['score'].empty else 0,
                rel_data['score'].std() if not rel_data['score'].empty else 0,
                rel_data['nodes_mapped'].mean() if not rel_data['nodes_mapped'].empty else 0
            ])
        
        stats_df = pd.DataFrame(stats_data, 
                               columns=['Relation', 'Count', 'Avg Score', 'Std Score', 'Avg Nodes'])
        
        table = plt.table(cellText=stats_df.round(3).values,
                         colLabels=stats_df.columns,
                         cellLoc='center',
                         loc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.5)
        plt.axis('off')
        plt.title('Summary Statistics by Relation Type')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'match_success_analysis.png'), dpi=300, bbox_inches='tight')
        plt.close()
    
    def create_comprehensive_dashboard(self):
        """Crea un dashboard completo con tutti i risultati"""
        print("Creating comprehensive dashboard...")
        
        # Create summary report
        report = {
            'analysis_date': datetime.now().isoformat(),
            'total_comparisons': len(self.df),
            'successful_matches': len(self.df[self.df['score'].notna()]),
            'unique_individuals': len(set(list(self.df['idA']) + list(self.df['idB']))),
            'relation_types': self.df['relation'].nunique(),
            'average_score': self.df['score'].mean(),
            'score_std': self.df['score'].std(),
            'avg_nodes_mapped': self.df['nodes_mapped'].mean()
        }
        
        # Save summary as JSON
        with open(os.path.join(self.output_dir, 'analysis_summary.json'), 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Create detailed CSV export
        self.df.to_csv(os.path.join(self.output_dir, 'all_data_processed.csv'), index=False)
        
        # Create heatmap of relationships
        plt.figure(figsize=(12, 10))
        
        # Relationship matrix
        relation_matrix = self.df.pivot_table(
            values='score', 
            index='idA', 
            columns='idB', 
            aggfunc='mean'
        )
        
        if not relation_matrix.empty:
            # Sample if too large
            if relation_matrix.shape[0] > 50:
                relation_matrix = relation_matrix.sample(n=50, axis=0).sample(n=50, axis=1)
            
            sns.heatmap(relation_matrix, cmap='viridis', cbar=True, 
                       square=True, linewidths=0.1)
            plt.title('Fingerprint Similarity Heatmap (Sample)')
            plt.xlabel('Fingerprint B')
            plt.ylabel('Fingerprint A')
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, 'similarity_heatmap.png'), dpi=300, bbox_inches='tight')
        
        plt.close()
        
        print(f"Analysis complete! Results saved in: {self.output_dir}")
        return report
    
    def run_complete_analysis(self):
        """Esegue l'analisi completa"""
        print("Starting complete fingerprint analysis...")
        
        if self.df.empty:
            print("No data loaded. Analysis cannot proceed.")
            return
        
        self.analyze_score_distributions()
        self.analyze_family_relationships() 
        self.analyze_match_success_rates()
        report = self.create_comprehensive_dashboard()
        
        print("\n=== ANALYSIS SUMMARY ===")
        print(f"Total comparisons: {report['total_comparisons']:,}")
        print(f"Successful matches: {report['successful_matches']:,}")
        print(f"Success rate: {(report['successful_matches']/report['total_comparisons']*100):.1f}%")
        print(f"Average score: {report['average_score']:.3f} ± {report['score_std']:.3f}")
        print(f"Average nodes mapped: {report['avg_nodes_mapped']:.1f}")
        print(f"Unique individuals: {report['unique_individuals']}")
        print(f"Results saved in: {self.output_dir}")
        
        return report

if __name__ == "__main__":
    # Initialize analyzer
    analyzer = FingerprintAnalyzer()
    
    # Run complete analysis
    analyzer.run_complete_analysis()