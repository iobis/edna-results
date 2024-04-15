import os
import pandas as pd
from util import download_results, fetch_metadata, fetch_metadata, derive_marker_name, get_folders_by_site, fetch_metadata_df


PROJECT_NAMES = ["eDNAexpeditions_batch1_samples", "eDNAexpeditions_batch2_samples"]
OCCURRENCE_FILE = "Occurrence_table.tsv"
DNA_FILE = "DNA_extension_table.tsv"
OUPUT_FOLDER = "output"
# TODO: read contaminants from JSON
CONTAMINANTS = ["Homo", "Sus", "Gallus", "Canis", "Bos", "Felis", "Ovis", "Mus", "Vulpes", "Rattus", "Capra", "Rangifer", "Macaca"]
REMOVE_CONTAMINANTS = True
REMOVE_BLANK = True

# download pipeline results from GitHub

download_results()

# fetch metadata from PlutoF and format

metadata_df = fetch_metadata_df(REMOVE_BLANK)

# process by site

folders_by_site = get_folders_by_site(PROJECT_NAMES)

for site_name in folders_by_site:

    occurrence_tables = []
    dna_tables = []

    datasets = folders_by_site[site_name]

    for dataset in datasets:
        marker = derive_marker_name(dataset)
        dataset_path = os.path.join(dataset, "05-dwca")

        occurrence_path = os.path.join(dataset_path, OCCURRENCE_FILE)
        dna_path = os.path.join(dataset_path, DNA_FILE)

        if not os.path.exists(occurrence_path):
            print(f"Missing file {occurrence_path}")
            continue
        if not os.path.exists(dna_path):
            print(f"Missing file {dna_path}")
            continue

        # read source files

        occurrence = pd.read_csv(occurrence_path, sep="\t")
        dna = pd.read_csv(dna_path, sep="\t")

        # update occurrenceID

        occurrence["occurrenceID"] = occurrence["occurrenceID"].apply(lambda x: f"{x}_{marker}")
        dna["occurrenceID"] = dna["occurrenceID"].apply(lambda x: f"{x}_{marker}")

        # add batch

        if "batch1" in dataset:
            occurrence["eventRemarks"] = "sequencing batch 1"
        elif "batch2" in dataset:
            occurrence["eventRemarks"] = "sequencing batch 2"

        # append

        occurrence_tables.append(occurrence)
        dna_tables.append(dna)

    # concat

    if len(occurrence_tables) != len(dna_tables) or len(occurrence_tables) == 0:
        print(f"Skipping {site_name} due to missing data")
        continue

    occurrence_combined = pd.concat(occurrence_tables)
    dna_combined = pd.concat(dna_tables)

    # replace sample ID EE0476 with EE0475

    occurrence_combined["occurrenceID"] = occurrence_combined["occurrenceID"].str.replace("EE0476", "EE0475")
    occurrence_combined["materialSampleID"] = occurrence_combined["materialSampleID"].str.replace("EE0476", "EE0475")
    dna_combined["occurrenceID"] = dna_combined["occurrenceID"].str.replace("EE0476", "EE0475")

    # merge metadata

    occurrence_combined = pd.merge(occurrence_combined, metadata_df, on="materialSampleID", how="inner")

    # remove contaminants

    if REMOVE_CONTAMINANTS:
        contaminants = occurrence_combined[occurrence_combined["genus"].isin(CONTAMINANTS)]
        contaminant_ids = contaminants["occurrenceID"].tolist()
        occurrence_combined = occurrence_combined[~occurrence_combined["occurrenceID"].isin(contaminant_ids)]
        dna_combined = dna_combined[~dna_combined["occurrenceID"].isin(contaminant_ids)]

    # output

    if not os.path.exists(OUPUT_FOLDER):
        os.makedirs(OUPUT_FOLDER)

    occurrence_combined.to_csv(os.path.join("output", f"{site_name}_Occurrence.tsv"), sep="\t", index=False)
    dna_combined.to_csv(os.path.join("output", f"{site_name}_DNADerivedData.tsv"), sep="\t", index=False)
