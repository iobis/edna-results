import os
import pandas as pd
from util import download_results, derive_marker_name, get_folders_by_site, fetch_metadata_df
import json
import pyworms


PROJECT_NAMES = ["eDNAexpeditions_batch1_samples", "eDNAexpeditions_batch2_samples"]
OCCURRENCE_FILE = "Occurrence_table.tsv"
DNA_FILE = "DNA_extension_table.tsv"
OUPUT_FOLDER = "output"
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

    # apply annotations

    with open(f"annotations/{site_name}.json") as f:
        annotations = json.load(f)
        for annotation in annotations:

            if "species" in annotation:
                field = "scientificName"
                name = annotation["species"].strip()
            elif "genus" in annotation:
                field = "genus"
                name = annotation["genus"].strip()
            elif "family" in annotation:
                field = "family"
                name = annotation["family"].strip()
            elif "order" in annotation:
                field = "order"
                name = annotation["order"].strip()
            elif "class" in annotation:
                field = "class"
                name = annotation["class"].strip()
            elif "phylum" in annotation:
                field = "phylum"
                name = annotation["phylum"].strip()

            if annotation["remove"] == True or annotation["remove"] == "true":

                print(f"Removing {field} {name} from {site_name}")
                # TODO: use higher taxon (phylum?) for scientificName and scientificNameID
                occurrence_ids = list(occurrence_combined.loc[occurrence_combined[field] == name]["occurrenceID"])
                occurrence_combined.loc[occurrence_combined["occurrenceID"].isin(occurrence_ids), ["class", "order", "family", "genus", "taxonRank"]] = None
                occurrence_combined.loc[occurrence_combined["occurrenceID"].isin(occurrence_ids), ["scientificName"]] = "incertae sedis"
                occurrence_combined.loc[occurrence_combined["occurrenceID"].isin(occurrence_ids), ["scientificNameID"]] = "urn:lsid:marinespecies.org:taxname:12"
                occurrence_combined.loc[occurrence_combined["occurrenceID"].isin(occurrence_ids), ["identificationRemarks"]] = "scientificName changed due to a manual annotation; " + occurrence_combined.loc[occurrence_combined["occurrenceID"].isin(occurrence_ids), ["identificationRemarks"]]

            if (annotation["remove"] == False or annotation["remove"] == "false") and "new_AphiaID" in annotation:

                print(f"Updating {field} {name} for {site_name}")
                occurrence_ids = list(occurrence_combined.loc[occurrence_combined[field] == name]["occurrenceID"])
                new_taxon = pyworms.aphiaRecordByAphiaID(str(annotation["new_AphiaID"]).strip())
                occurrence_combined.loc[occurrence_combined["occurrenceID"].isin(occurrence_ids), ["kingdom"]] = new_taxon["kingdom"]
                occurrence_combined.loc[occurrence_combined["occurrenceID"].isin(occurrence_ids), ["phylum"]] = new_taxon["phylum"]
                occurrence_combined.loc[occurrence_combined["occurrenceID"].isin(occurrence_ids), ["class"]] = new_taxon["class"]
                occurrence_combined.loc[occurrence_combined["occurrenceID"].isin(occurrence_ids), ["order"]] = new_taxon["order"]
                occurrence_combined.loc[occurrence_combined["occurrenceID"].isin(occurrence_ids), ["family"]] = new_taxon["family"]
                occurrence_combined.loc[occurrence_combined["occurrenceID"].isin(occurrence_ids), ["genus"]] = new_taxon["genus"]
                occurrence_combined.loc[occurrence_combined["occurrenceID"].isin(occurrence_ids), ["scientificName"]] = new_taxon["scientificname"]
                occurrence_combined.loc[occurrence_combined["occurrenceID"].isin(occurrence_ids), ["scientificNameID"]] = new_taxon["lsid"]
                occurrence_combined.loc[occurrence_combined["occurrenceID"].isin(occurrence_ids), ["taxonRank"]] = new_taxon["rank"].lower()
                occurrence_combined.loc[occurrence_combined["occurrenceID"].isin(occurrence_ids), ["identificationRemarks"]] = "scientificName changed due to a manual annotation; " + occurrence_combined.loc[occurrence_combined["occurrenceID"].isin(occurrence_ids), ["identificationRemarks"]]

    # remove contaminants

    if REMOVE_CONTAMINANTS:

        with open(f"annotations/contaminants.json") as f:
            annotations = json.load(f)

        for annotation in annotations:
            for rank, name in annotation.items():
                print(f"Removing {rank} {name} from {site_name}")
                occurrence_ids = list(occurrence_combined.loc[occurrence_combined[rank.strip()] == name.strip()]["occurrenceID"])
                occurrence_combined = occurrence_combined[~occurrence_combined["occurrenceID"].isin(occurrence_ids)]
                dna_combined = dna_combined[~dna_combined["occurrenceID"].isin(occurrence_ids)]

    # output

    if not os.path.exists(OUPUT_FOLDER):
        os.makedirs(OUPUT_FOLDER)

    occurrence_combined.to_csv(os.path.join("output", f"{site_name}_Occurrence.tsv"), sep="\t", index=False)
    dna_combined.to_csv(os.path.join("output", f"{site_name}_DNADerivedData.tsv"), sep="\t", index=False)
