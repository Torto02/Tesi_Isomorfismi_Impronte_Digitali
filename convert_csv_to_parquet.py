import os
import pandas as pd

def convert_csv_to_parquet(base_dir):
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.csv'):
                csv_path = os.path.join(root, file)
                parquet_path = os.path.splitext(csv_path)[0] + '.parquet'
                
                # Controlla se il file Parquet esiste già
            
                
                try:
                    # Legge il file CSV
                    df = pd.read_csv(csv_path)
                    # Converte in Parquet
                    # if os.path.exists(parquet_path):
                    #     print(f"Skipped (already exists): {parquet_path}")
                    # else:
                    #     df.to_parquet(parquet_path, index=False)
                    #     print(f"Converted: {csv_path} -> {parquet_path}")

                    # Elimina il file CSV originale
                    os.remove(csv_path)
                    print(f"Deleted: {csv_path}")
                except Exception as e:
                    print(f"Error converting {csv_path}: {e}")

if __name__ == "__main__":
    base_directory = "OutputMatrices"  # Percorso base della struttura
    convert_csv_to_parquet(base_directory)
