import os
import pandas as pd
import matplotlib.pyplot as plt
import uuid
from datetime import datetime

# Base paths: aggiungi tutte le directory necessarie
BASE_DIRS = [
    "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/0",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/1",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/2",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/3",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/4",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/5",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/6",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/7",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/8",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/9",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/10",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/11",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/12",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/13",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/14",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/15",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/16",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/17",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/18",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/19",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/20",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/21",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/22",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/23",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/24",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/25",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/26",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/27",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/28",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/29",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/30",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/31",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/32",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/33",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/34",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/35",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/36",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/37",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/38",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/39",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/40",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/41",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/42",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/43",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/44",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/45",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/46",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/47",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/48",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/49",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/50",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/51",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/52",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/53",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/54",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/55",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/56",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/57",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/58",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/59",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/60",
    # "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons/61",
]
OUTPUT_DIR = "relations_comparisons"
unique_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
OUTPUT_SUBDIR = os.path.join(OUTPUT_DIR, unique_id)
os.makedirs(OUTPUT_SUBDIR, exist_ok=True)

# Raccoglie tutti i CSV nelle sottocartelle
csv_files = []
for base_dir in BASE_DIRS:
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".csv"):
                csv_files.append(os.path.join(root, file))

# Cerca anche i file JSON nelle stesse cartelle
json_files = []
for base_dir in BASE_DIRS:
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".json"):
                json_files.append(os.path.join(root, file))

# Carica e unisce tutti i CSV
all_rows = []
for path in csv_files:
    try:
        df = pd.read_csv(path)
        all_rows.append(df)
    except Exception as e:
        print(f"Errore nel file {path}: {e}")

if not all_rows:
    print("Nessun file CSV trovato.")
    exit()

# Unione in un unico DataFrame
merged_df = pd.concat(all_rows, ignore_index=True)

# Conta il numero totale di file CSV
total_files = len(csv_files)

# Conteggio totale dei match per relation
match_counts = {}

# Conteggio di quanti file contengono almeno un match per ogni relation
files_with_relation = {}

for path in csv_files:
    try:
        df = pd.read_csv(path)
        
        # Filtra le relazioni "unknown"
        df = df[df["relation"] != "unknown"]

        # Conteggio dei match
        for rel in df["relation"]:
            match_counts[rel] = match_counts.get(rel, 0) + 1

        # Conteggio dei file
        for rel in df["relation"].unique():
            files_with_relation[rel] = files_with_relation.get(rel, 0) + 1

    except Exception as e:
        print(f"Errore nel file {path}: {e}")

total_files_by_relation = {}

for path in csv_files:
    try:
        df = pd.read_csv(path)
        # Filtra le relazioni "unknown"
        df = df[df["relation"] != "unknown"]
        
        for rel in df["relation"].unique():
            total_files_by_relation[rel] = total_files_by_relation.get(rel, 0) + 1
    except:
        continue

relation_presence_percentages = {
    rel: (files_with_relation.get(rel, 0) / total_files_by_relation.get(rel, 1)) * 100
    for rel in total_files_by_relation
}

relation_presence_percentages = dict(sorted(relation_presence_percentages.items(), key=lambda x: x[1], reverse=True))

# Calcola score medio per relazione leggendo dai CSV (colonna 'score')
scores_by_relation = {}

for path in csv_files:
    try:
        df = pd.read_csv(path)
        # Filtra le relazioni "unknown"
        df = df[df["relation"] != "unknown"]
        
        if "score" in df.columns and "relation" in df.columns:
            for rel in df["relation"].unique():
                scores = df.loc[df["relation"] == rel, "score"]
                valid_scores = scores.dropna()
                if not valid_scores.empty:
                    scores_by_relation.setdefault(rel, []).extend(valid_scores.tolist())
    except Exception as e:
        print(f"Errore nel file {path} durante il calcolo degli score: {e}")

# Calcola score medio per relazione
avg_scores = {rel: sum(scores) / len(scores) for rel, scores in scores_by_relation.items() if scores}
avg_scores = dict(sorted(avg_scores.items(), key=lambda x: x[1], reverse=True))

# Calcolo percentuale: match per relation diviso numero di file che la contengono
relation_percentages = {
    rel: (match_counts[rel] / files_with_relation[rel]) * 100
    for rel in match_counts
}

# Ordina per percentuale decrescente
relation_percentages = dict(sorted(relation_percentages.items(), key=lambda x: x[1], reverse=True))

# Stampa
print("Percentuale media di match per file (per tipo di relazione):")
for rel, perc in relation_percentages.items():
    print(f"{rel}: {perc:.2f}%")

# Stampa score medio per relazione
print("\nScore medio per tipo di relazione:")
for rel, score in avg_scores.items():
    print(f"{rel}: {score:.3f}")

# --- Unificazione relazioni in "same_family" ---
# Mappa per relazioni familiari
family_mapping = {
    "twins": "same_family",
    "siblings": "same_family",
    "child_father": "same_family",
}

combined_match_counts = {}
combined_files_with_relation = {}

for rel in match_counts:
    key = family_mapping.get(rel, rel)
    combined_match_counts[key] = combined_match_counts.get(key, 0) + match_counts[rel]

for rel in files_with_relation:
    key = family_mapping.get(rel, rel)
    combined_files_with_relation[key] = combined_files_with_relation.get(key, 0) + files_with_relation[rel]

combined_percentages = {
    rel: (combined_match_counts[rel] / combined_files_with_relation[rel]) * 100
    for rel in combined_match_counts
}

combined_percentages = dict(sorted(combined_percentages.items(), key=lambda x: x[1], reverse=True))

# Grafico a barre
plt.figure(figsize=(10, 6))
plt.bar(relation_percentages.keys(), relation_percentages.values())
plt.title("Media di match per file per tipo di relazione")
plt.xlabel("Relazione")
plt.ylabel("Match medi per file")
plt.xticks(rotation=45)
plt.tight_layout()
plt.grid(axis="y")
plt.savefig(os.path.join(OUTPUT_SUBDIR, "media_match_per_file.png"))
plt.close()

# Grafico score medio
plt.figure(figsize=(10, 6))
plt.bar(avg_scores.keys(), avg_scores.values())
plt.title("Score medio per tipo di relazione")
plt.xlabel("Relazione")
plt.ylabel("Score medio")
plt.xticks(rotation=45)
plt.tight_layout()
plt.grid(axis="y")
plt.savefig(os.path.join(OUTPUT_SUBDIR, "score_medio.png"))
plt.close()

# Grafico aggregato per famiglie
plt.figure(figsize=(10, 6))
plt.bar(combined_percentages.keys(), combined_percentages.values())
plt.title("Media match per file (aggregata per famiglie)")
plt.xlabel("Relazione")
plt.ylabel("Match medi per file")
plt.xticks(rotation=45)
plt.tight_layout()
plt.grid(axis="y")
plt.savefig(os.path.join(OUTPUT_SUBDIR, "match_per_file_same_family.png"))
plt.close()

# Nuovo grafico: percentuale di file con almeno un match
plt.figure(figsize=(10, 6))
plt.bar(relation_presence_percentages.keys(), relation_presence_percentages.values())
plt.title("Percentuale di file con almeno un match per tipo di relazione")
plt.xlabel("Relazione")
plt.ylabel("Percentuale (%)")
plt.xticks(rotation=45)
plt.tight_layout()
plt.grid(axis="y")
plt.savefig(os.path.join(OUTPUT_SUBDIR, "percentuale_file_con_match.png"))
plt.close()