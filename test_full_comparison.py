#!/usr/bin/env python3
"""
Script di test completo per verificare una comparazione usando la nuova zona intermedia
"""

import subprocess
import os
import sys

def test_full_comparison():
    """Test di una comparazione completa usando la nuova logica"""
    
    main_script_path = "/Users/riccardotortorelli/Desktop/Tesi/main_script.py"
    test_output_folder = "/Users/riccardotortorelli/Desktop/Tesi/test_zone_output"
    os.makedirs(test_output_folder, exist_ok=True)
    
    # Environment variables for the test
    env = os.environ.copy()
    env["OUTPUT_FOLDER"] = test_output_folder
    env["LOGGER_CSV_FILENAME"] = "test_comparison.csv"
    
    print("Running full comparison test with intermediate zone selection...")
    print("Test fingerprints: 01_Ay_03_01 vs 01_Ay_03_00")
    
    try:
        # Run main script with simulated input (fingerprint 4 vs fingerprint 3)
        result = subprocess.run(
            ["python3", main_script_path],
            env=env,
            input="4\n3\n",  # 01_Ay_03_01 vs 01_Ay_03_00
            text=True,
            capture_output=True,
            timeout=120  # 2 minutes timeout
        )
        
        print("=== STDOUT ===")
        print(result.stdout)
        
        if result.stderr:
            print("=== STDERR ===") 
            print(result.stderr)
        
        print(f"Return code: {result.returncode}")
        
        # Check if output file was created
        csv_file = os.path.join(test_output_folder, "test_comparison.csv")
        if os.path.exists(csv_file):
            print(f"✓ Output CSV created: {csv_file}")
            
            # Read and display first few lines
            with open(csv_file, 'r') as f:
                lines = f.readlines()
                print(f"CSV contains {len(lines)} lines")
                if len(lines) > 0:
                    print("First few lines:")
                    for i, line in enumerate(lines[:min(5, len(lines))]):
                        print(f"  {i+1}: {line.strip()}")
        else:
            print("✗ No output CSV found")
            
    except subprocess.TimeoutExpired:
        print("✗ Test timed out after 2 minutes")
    except Exception as e:
        print(f"✗ Test failed with error: {e}")

if __name__ == "__main__":
    test_full_comparison()