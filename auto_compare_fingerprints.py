import os
import subprocess
import time

# Path to the main script
main_script_path = "/Users/riccardotortorelli/Desktop/Tesi/main_script.py"

# Base folder for fingerprints
base_folder_impronte = "/Users/riccardotortorelli/Desktop/Tesi/Archivio/"

# Output folder for all comparisons
output_folder = "/Users/riccardotortorelli/Desktop/Tesi/All_comparisons"
os.makedirs(output_folder, exist_ok=True)

# Get all fingerprint folders
fingerprints = sorted([
    d for d in os.listdir(base_folder_impronte)
    if os.path.isdir(os.path.join(base_folder_impronte, d)) and not d.startswith('.')
])

if len(fingerprints) < 2:
    print("At least two fingerprint folders are required.")
    exit(1)

# Loop through all other fingerprints using only the first one as A
starttime = time.time()

fingerprintA = fingerprints[0]
for idxA in [61,62,63,64,65,66,67,68,69,70,71]:  # Esegui il ciclo per idxA = 1 e idxA = 2
    fingerprintA = fingerprints[idxA]
    for idxB, fingerprintB in enumerate(fingerprints):
        if idxA == idxB:
            continue

        print(f"Processing comparison: {fingerprintA} vs {fingerprintB}")
        
        # Create output folder for this idxA (e.g. All_comparisons/1 or All_comparisons/2)
        idxA_folder = os.path.join(output_folder, str(idxA))
        os.makedirs(idxA_folder, exist_ok=True)
        # The logger CSV will be saved in idxA_folder, named as fingerprintB.csv
        # Set environment variables for the subprocess
        env = os.environ.copy()
        env["BASE_FOLDER_IMPRONTE"] = base_folder_impronte
        env["OUTPUT_FOLDER"] = idxA_folder  # Save results in the idxA folder
        env["LOGGER_CSV_FILENAME"] = f"{fingerprintB}.csv"
        # Run the main script with simulated input for fingerprint selection
        subprocess.run(
            ["python3", main_script_path],
            env=env,
            input=f"{idxA + 1}\n{idxB + 1}\n",
            text=True
        )
endtime = time.time()
total = endtime - starttime
print(f"Start time: {starttime}, End time: {endtime}, Total time: {total} seconds")