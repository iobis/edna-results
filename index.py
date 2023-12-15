import os
import urllib.request, json 
import pandas as pd


PROJECT_NAME = "eDNAexpeditions_batch1_samples"
OCCURRENCE_FILE = "Occurrence_table.tsv"
DNA_FILE = "DNA_extension_table.tsv"
OUPUT_FOLDER = "output"
CONTAMINANTS = ["Homo", "Sus", "Gallus", "Canis", "Bos", "Felis", "Ovis", "Mus", "Vulpes", "Rattus", "Capra", "Rangifer"]
REMOVE_CONTAMINANTS = False


def download_results() -> None:
    if not os.path.exists("pacman-pipeline-results"):
        os.system("git clone --depth 1 https://github.com/iobis/pacman-pipeline-results.git")


def fetch_metadata() -> dict:
    with urllib.request.urlopen("https://raw.githubusercontent.com/iobis/edna-tracker-data/data/generated.json") as url:
        data = json.load(url)
        return data


def list_datasets() -> list:
    datasets = []
    root_folder = os.path.join("pacman-pipeline-results", PROJECT_NAME, "runs")
    for dataset in os.listdir(root_folder):
        if os.path.isdir(os.path.join(root_folder, dataset)):
            datasets.append(dataset)
    return datasets


def derive_site_name(input):
    site_dict = {
        "cocos": "cocos_island_national_park",
        "galapagos": "galapagos_islands",
        "coiba": "coiba_national_park_and_its_special_zone_of_marine_protection",
        "banc": "banc_d_arguin_national_park",
        "tubbataha": "tubbataha_reefs_natural_park",
        "wadden": "wadden_sea",
        "sundarbans": "the_sundarbans",
        "revillagigedo": "archipielago_de_revillagigedo",
        "everglades": "everglades_national_park",
        "aldabra": "aldabra_atoll",
        "lord": "lord_howe_island_group",
        "french": "french_austral_lands_and_seas",
        "shark": "shark_bay_western_australia",
        "isimangaliso": "isimangaliso_wetland_park",
        "porto": "gulf_of_porto_calanche_of_piana_gulf_of_girolata_scandola_reserve",
        "belize": "belize_barrier_reef_reserve_system",
        "lagoons": "lagoons_of_new_caledonia_reef_diversity_and_associated_ecosystems",
        "brazilian": "brazilian_atlantic_islands_fernando_de_noronha_and_atol_das_rocas_reserves",
        "ningaloo": "ningaloo_coast",
        "sanganeb": "sanganeb_marine_national_park_and_dungonab_bay_mukkawar_island_marine_national_park",
        "scandola": "gulf_of_porto_calanche_of_piana_gulf_of_girolata_scandola_reserve",
        "brazil": "brazilian_atlantic_islands_fernando_de_noronha_and_atol_das_rocas_reserves",
        "mauritania": "banc_d_arguin_national_park",
        "southernocean": "french_austral_lands_and_seas",
        "newcaledonia": "lagoons_of_new_caledonia_reef_diversity_and_associated_ecosystems",
        "philippines": "tubbataha_reefs_natural_park",
        "bangladesh": "the_sundarbans",
        "southafrica": "isimangaliso_wetland_park",
        "seychel": "aldabra_atoll",
        "mexico": "archipielago_de_revillagigedo"
    }
    input_lower = input.lower()
    for key in site_dict:
        if input_lower.startswith(key):
            return site_dict[key]
    raise Exception(f"Site {input} not recognized")


def derive_marker_name(input: str) -> str:
    marker_dict = {
        "mimammal": "12s_mimammal",
        "mifish": "12s_mifish",
        "teleo": "12s_teleo",
        "coi": "coi",
        "co1": "coi",
        "16s": "16s",
    }
    input_marker = input.split("_")[1]
    input_lower = input_marker.lower()
    for key in marker_dict:
        if key in input_lower:
            return marker_dict[key]
    raise Exception(f"Marker {input} not recognized")


# download pipeline results from GitHub

download_results()

# fetch metadata from PlutoF and format

metadata = fetch_metadata()
metadata_df = pd.DataFrame.from_dict([{
    "materialSampleID": sample["name"],
    "locality": sample["area_locality"],
    "decimalLongitude": sample["area_longitude"],
    "decimalLatitude": sample["area_latitude"],
    "sampleSize": sample["size"],
    "higherGeography": sample["parent_area_name"]
} for sample in metadata["samples"]])

# organize data folders by site

dataset_folders = list_datasets()

folders_by_site = {}
for dataset_folder in dataset_folders:
    dataset_name = derive_site_name(dataset_folder)
    if dataset_name not in folders_by_site:
        folders_by_site[dataset_name] = []
    folders_by_site[dataset_name].append(dataset_folder)

# process by site

for site_name in folders_by_site:

    occurrence_tables = []
    dna_tables = []

    datasets = folders_by_site[site_name]

    for dataset in datasets:
        marker = derive_marker_name(dataset)
        dataset_path = os.path.join("pacman-pipeline-results", PROJECT_NAME, "runs", dataset, "05-dwca")

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

    occurrence_combined = pd.merge(occurrence_combined, metadata_df, on="materialSampleID", how="left")

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
