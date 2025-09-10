#!/usr/bin/env python3
"""
Script per correggere la relazione errata nei file CSV.
Corregge "same_family" in "child_father" per confronti tra impronte 02_Ax_* e 02_B0_* (in entrambe le direzioni).
"""

import os
import pandas as pd
from pathlib import Path
import re

class CSVRelationFixer:
    def __init__(self, base_dir="All_comparisons"):
        self.base_dir = Path(base_dir)
        self.corrections_made = 0
        self.files_processed = 0
        self.files_modified = 0
        
    def should_correct_relation(self, idA, idB, current_relation):
        """
        Determina se la relazione deve essere corretta.
        Controlla entrambe le direzioni: A vs B e B vs A
        
        Args:
            idA: ID dell'impronta A
            idB: ID dell'impronta B  
            current_relation: Relazione attuale
            
        Returns:
            True se deve essere corretta da same_family a child_father
        """
        # Verifica se la relazione attuale è same_family
        if current_relation != "same_family":
            return False
            
        try:
            # Converti in stringhe per sicurezza
            str_idA = str(idA)
            str_idB = str(idB)
            
            # Pattern per 02_Ax_* (dove x è qualsiasi carattere dopo A)
            pattern_Ax = re.match(r'^02_A[^_]*_.*', str_idA)
            pattern_B0 = re.match(r'^02_B0_.*', str_idB)
            
            # Caso 1: idA = 02_Ax_* e idB = 02_B0_*
            if pattern_Ax and pattern_B0:
                print(f"  Trovato pattern da correggere: {str_idA} (figlio) vs {str_idB} (padre)")
                return True
            
            # Caso 2: idA = 02_B0_* e idB = 02_Ax_* (direzione inversa)
            pattern_Ax_B = re.match(r'^02_A[^_]*_.*', str_idB)
            pattern_B0_A = re.match(r'^02_B0_.*', str_idA)
            
            if pattern_B0_A and pattern_Ax_B:
                print(f"  Trovato pattern da correggere (inverso): {str_idA} (padre) vs {str_idB} (figlio)")
                return True
                
        except Exception as e:
            print(f"  Errore nel parsing: {e}")
            
        return False
    
    def fix_csv_file(self, csv_file_path):
        """
        Corregge un singolo file CSV.
        
        Args:
            csv_file_path: Path al file CSV da correggere
            
        Returns:
            Numero di correzioni effettuate in questo file
        """
        try:
            # Carica il CSV
            df = pd.read_csv(csv_file_path)
            
            if df.empty:
                return 0
                
            corrections_in_file = 0
            
            # Itera attraverso le righe per trovare quelle da correggere
            for idx, row in df.iterrows():
                if self.should_correct_relation(row.get('idA'), row.get('idB'), row.get('relation')):
                    # Effettua la correzione
                    df.at[idx, 'relation'] = 'child_father'
                    corrections_in_file += 1
                    print(f"    Correzione {corrections_in_file}: {row.get('idA')} vs {row.get('idB')}")
            
            # Salva il file solo se ci sono state correzioni
            if corrections_in_file > 0:
                df.to_csv(csv_file_path, index=False)
                print(f"  File salvato con {corrections_in_file} correzioni")
                
            return corrections_in_file
            
        except Exception as e:
            print(f"  Errore nel processare {csv_file_path}: {e}")
            return 0
    
    def scan_and_fix_all(self):
        """
        Scansiona tutte le sottocartelle e corregge i file CSV.
        """
        if not self.base_dir.exists():
            print(f"Errore: Directory {self.base_dir} non trovata!")
            return
            
        print(f"Scansionando directory: {self.base_dir.absolute()}")
        
        # Trova tutti i file CSV nelle sottocartelle
        csv_files = list(self.base_dir.rglob("*.csv"))
        
        if not csv_files:
            print("Nessun file CSV trovato!")
            return
            
        print(f"Trovati {len(csv_files)} file CSV da processare\n")
        
        for csv_file in csv_files:
            print(f"Processando: {csv_file.relative_to(self.base_dir)}")
            self.files_processed += 1
            
            corrections = self.fix_csv_file(csv_file)
            
            if corrections > 0:
                self.files_modified += 1
                self.corrections_made += corrections
            else:
                print("  Nessuna correzione necessaria")
                
            print()  # Riga vuota per separare
    
    def print_summary(self):
        """Stampa un riassunto delle correzioni effettuate."""
        print("=" * 60)
        print("RIASSUNTO CORREZIONI")
        print("=" * 60)
        print(f"File processati: {self.files_processed}")
        print(f"File modificati: {self.files_modified}")
        print(f"Correzioni totali: {self.corrections_made}")
        
        if self.corrections_made > 0:
            print(f"\n✅ Correzioni completate con successo!")
            print(f"Tutte le relazioni 'same_family' tra:")
            print(f"  - 02_Ax_* ↔ 02_B0_* (figlio ↔ padre)")
            print(f"sono state corrette in 'child_father'")
        else:
            print(f"\nℹ️  Nessuna correzione necessaria")

def main():
    """Funzione principale."""
    print("=== CORRETTORE RELAZIONI CSV ===\n")
    print("Questo script corregge relazioni errate nei file CSV:")
    print("- Cerca confronti tra impronte 02_Ax_* e 02_B0_* (in entrambe le direzioni)")
    print("- Cambia 'same_family' in 'child_father' per questi pattern")
    print()
    
    # Controlla se la directory All_comparisons esiste
    base_dir = "All_comparisons"
    if not Path(base_dir).exists():
        print(f"Errore: Directory {base_dir} non trovata!")
        print("Assicurati di eseguire lo script dalla directory corretta.")
        return
    
    # Conferma dall'utente
    response = input(f"Vuoi procedere con la correzione dei file CSV in '{base_dir}'? (s/N): ").lower()
    if response not in ['s', 'si', 'y', 'yes']:
        print("Operazione annullata.")
        return
    
    print("\nInizio elaborazione...\n")
    
    # Crea e esegui il correttore
    fixer = CSVRelationFixer(base_dir)
    fixer.scan_and_fix_all()
    fixer.print_summary()

if __name__ == "__main__":
    main()