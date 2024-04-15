import os
import urllib.request
import json
import pandas as pd


def download_results() -> None:
    if not os.path.exists("pacman-pipeline-results"):
        os.system("git clone --depth 1 https://github.com/iobis/pacman-pipeline-results.git")


def fetch_metadata() -> dict:
    with urllib.request.urlopen("https://raw.githubusercontent.com/iobis/edna-tracker-data/data/generated.json") as url:
        data = json.load(url)
        return data


def fetch_metadata_df(remove_blank):
    metadata = fetch_metadata()

    metadata_df = pd.DataFrame.from_dict([{
        "materialSampleID": sample["name"],
        "locality": sample["area_locality"],
        "decimalLongitude": sample["area_longitude"],
        "decimalLatitude": sample["area_latitude"],
        "sampleSize": sample["size"],
        "higherGeography": sample["parent_area_name"],
        "blank": sample["blank"],
        "locationID": sample["station"]
    } for sample in metadata["samples"]])

    if remove_blank:
        metadata_df = metadata_df[metadata_df["blank"] == False]

    metadata_df = metadata_df.drop(columns=["blank"])
    return metadata_df


def list_datasets(project_names) -> list:
    datasets = []
    for project_name in project_names:
        root_folder = os.path.join("pacman-pipeline-results", project_name, "runs")
        for dataset in os.listdir(root_folder):
            if os.path.isdir(os.path.join(root_folder, dataset)):
                datasets.append(os.path.join(root_folder, dataset))
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
        "mexico": "archipielago_de_revillagigedo",
        "yemen": "socotra_archipelago",
        "argentina": "peninsula_valdes"
    }
    input_lower = input.split("/")[-1].lower()
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
    input_marker = input.split("/")[-1].split("_")[1]
    input_lower = input_marker.lower()
    for key in marker_dict:
        if key in input_lower:
            return marker_dict[key]
    raise Exception(f"Marker {input} not recognized")


def get_folders_by_site(project_names):
    dataset_folders = list_datasets(project_names)

    folders_by_site = {}

    for dataset_folder in dataset_folders:
        dataset_name = derive_site_name(dataset_folder)
        if dataset_name not in folders_by_site:
            folders_by_site[dataset_name] = []
        folders_by_site[dataset_name].append(dataset_folder)

    return folders_by_site
