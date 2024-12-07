import os
import pandas as pd
from ednaresults.util import derive_marker_name, derive_site_name
import json
import pyworms
import urllib.request
import logging
import shutil
import boto3
from botocore.exceptions import NoCredentialsError
from ednaresults.aphia import add_aphiaid, add_accepted_aphiaid, add_taxonomy
from termcolor import colored


class OccurrenceBuilder():

    def __init__(
        self,
        project_names=["eDNAexpeditions_batch1_samples", "eDNAexpeditions_batch2_samples"],
        occurrence_file="Occurrence_table.tsv",
        dna_file="DNA_extension_table.tsv",
        pipeline_data_path="./pipeline_data/",
        output_folder="output",
        remove_contaminants=True,
        list_generator=None,
        sync_results=True
    ):
        self.project_names = project_names
        self.occurrence_file = occurrence_file
        self.dna_file = dna_file
        self.pipeline_data_path = pipeline_data_path
        self.output_folder = output_folder
        self.remove_contaminants = remove_contaminants
        self.list_generator = list_generator
        self.sync_results = sync_results

    def build(self):

        # download pipeline results from GitHub

        if self.sync_results:
            self.download_results()

        # fetch metadata from PlutoF and format

        metadata_df = self.fetch_metadata_df()

        # prepare output folder

        self.prepare_output_folder()

        # process by site

        folders_by_site = self.get_folders_by_site()

        for site_name in folders_by_site:

            logging.info(colored(f"Processing {site_name} data", "green"))

            occurrence_tables = []
            dna_tables = []

            datasets = folders_by_site[site_name]

            for dataset in datasets:
                marker = derive_marker_name(dataset)
                dataset_path = os.path.join(dataset, "05-dwca")

                occurrence_path = os.path.join(dataset_path, self.occurrence_file)
                dna_path = os.path.join(dataset_path, self.dna_file)

                if not os.path.exists(occurrence_path):
                    logging.warn(f"Missing file {occurrence_path}")
                    continue
                if not os.path.exists(dna_path):
                    logging.warn(f"Missing file {dna_path}")
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

            # combine across samples and markers

            if len(occurrence_tables) != len(dna_tables) or len(occurrence_tables) == 0:
                logging.warn(f"Skipping {site_name} due to missing data")
                continue

            occurrence_combined = pd.concat(occurrence_tables)
            dna_combined = pd.concat(dna_tables)

            # replace sample ID EE0476 with EE0475

            occurrence_combined["occurrenceID"] = occurrence_combined["occurrenceID"].str.replace("EE0476", "EE0475")
            occurrence_combined["materialSampleID"] = occurrence_combined["materialSampleID"].str.replace("EE0476", "EE0475")
            dna_combined["occurrenceID"] = dna_combined["occurrenceID"].str.replace("EE0476", "EE0475")

            # merge metadata, move blanks into separate table

            metadata_df_blank = metadata_df[metadata_df["blank"] == True]
            metadata_df_notblank = metadata_df[metadata_df["blank"] == False]

            occurrence_combined_blank = pd.merge(occurrence_combined, metadata_df_blank, on="materialSampleID", how="inner")
            occurrence_combined_notblank = pd.merge(occurrence_combined, metadata_df_notblank, on="materialSampleID", how="inner")

            # replace taxonomy

            occurrence_combined_notblank = self.replace_taxonomy(occurrence_combined_notblank)

            # apply annotations

            occurrence_combined_notblank = self.apply_annotations(occurrence_combined_notblank, site_name)

            # cleanup dna tables

            occurrence_ids_blank = list(occurrence_combined_blank["occurrenceID"])
            occurrence_ids_notblank = list(occurrence_combined_notblank["occurrenceID"])

            dna_combined_blank = dna_combined[dna_combined["occurrenceID"].isin(occurrence_ids_blank)]
            dna_combined_notblank = dna_combined[dna_combined["occurrenceID"].isin(occurrence_ids_notblank)]

            # remove singletons from non blank data

            read_counts = pd.merge(
                occurrence_combined_notblank[["occurrenceID", "organismQuantity"]],
                dna_combined_notblank[["occurrenceID", "DNA_sequence"]],
                on="occurrenceID"
            ).groupby("DNA_sequence", as_index=False).agg({"organismQuantity": "sum"})
            singletons = read_counts[read_counts["organismQuantity"] == 1]
            singleton_ids = dna_combined_notblank[dna_combined_notblank["DNA_sequence"].isin(singletons["DNA_sequence"])]["occurrenceID"]

            occurrence_combined_notblank = occurrence_combined_notblank[~occurrence_combined_notblank["occurrenceID"].isin(singleton_ids)]
            dna_combined_notblank = dna_combined_notblank[~dna_combined_notblank["occurrenceID"].isin(singleton_ids)]

            # remove all A or all C

            all_ac_ids = dna_combined_notblank[dna_combined_notblank["DNA_sequence"].str.fullmatch(r"[AC]+")]["occurrenceID"].tolist()
            occurrence_combined_notblank = occurrence_combined_notblank[~occurrence_combined_notblank["occurrenceID"].isin(all_ac_ids)]
            dna_combined_notblank = dna_combined_notblank[~dna_combined_notblank["occurrenceID"].isin(all_ac_ids)]

            # output

            occurrence_combined_blank.to_csv(os.path.join(self.output_folder, "blank", f"{site_name}_Occurrence.tsv"), sep="\t", index=False)
            dna_combined_blank.to_csv(os.path.join(self.output_folder, "blank", f"{site_name}_DNADerivedData.tsv"), sep="\t", index=False)

            occurrence_combined_notblank.to_csv(os.path.join(self.output_folder, f"{site_name}_Occurrence.tsv"), sep="\t", index=False)
            dna_combined_notblank.to_csv(os.path.join(self.output_folder, f"{site_name}_DNADerivedData.tsv"), sep="\t", index=False)

            # species lists

            if self.list_generator is not None:
                self.list_generator.run(site_name, occurrence_combined_notblank, dna_combined_notblank, metadata_df_notblank)

    def prepare_output_folder(self):
        logging.warn(f"Clearing output directory {self.output_folder}")
        shutil.rmtree(self.output_folder, ignore_errors=True)
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)
        if not os.path.exists(os.path.join(self.output_folder, "blank")):
            os.makedirs(os.path.join(self.output_folder, "blank"))

        if self.list_generator is not None:
            self.list_generator.prepare_output_folder()

    def download_results(self) -> None:
        logging.warning("Syncing pipeline results to pipeline_data")
        os.system(f"aws s3 sync s3://obis-backups/edna_expeditions/pipeline_results/20240705/ ./pipeline_data/")

    def fetch_metadata(self) -> dict:
        metadata_url = "https://raw.githubusercontent.com/iobis/edna-tracker-data/data/generated.json"
        logging.info(f"Downloading metadata from {metadata_url}")
        with urllib.request.urlopen(metadata_url) as url:
            data = json.load(url)
            return data

    def fetch_metadata_df(self):
        logging.info("Fetching metadata from PlutoF")
        metadata = self.fetch_metadata()

        metadata_df = pd.DataFrame.from_dict([{
            "materialSampleID": sample["name"],
            "locality": sample["area_locality"],
            "decimalLongitude": sample["area_longitude"],
            "decimalLatitude": sample["area_latitude"],
            "sampleSize": sample["size"],
            "higherGeography": sample["parent_area_name"],
            "blank": sample["blank"],
            "locationID": sample["station"],
            "eventDate": sample["event_begin"],
        } for sample in metadata["samples"]])

        return metadata_df

    def list_datasets(self) -> list:
        datasets = []
        for project_name in self.project_names:
            root_folder = os.path.join(self.pipeline_data_path, project_name, "runs")
            for dataset in os.listdir(root_folder):
                if os.path.isdir(os.path.join(root_folder, dataset)):
                    datasets.append(os.path.join(root_folder, dataset))
        return datasets

    def get_folders_by_site(self):
        dataset_folders = self.list_datasets()

        folders_by_site = {}

        for dataset_folder in dataset_folders:
            dataset_name = derive_site_name(dataset_folder)
            if dataset_name not in folders_by_site:
                folders_by_site[dataset_name] = []
            folders_by_site[dataset_name].append(dataset_folder)

        return folders_by_site

    def replace_taxonomy(self, df: pd.DataFrame) -> pd.DataFrame:

        df = add_aphiaid(df)
        df = add_accepted_aphiaid(df)
        df["verbatimIdentification"] = df["scientificName"]
        df = add_taxonomy(df)
        return df

    def apply_annotations(self, df_occurrence: pd.DataFrame, site_name: str) -> pd.DataFrame:

        names_before = df_occurrence["scientificName"].nunique()

        with open(f"annotations/{site_name}.json") as f:
            annotations = json.load(f)
            logging.info(f"Applying {len(annotations)} annotations for {site_name} ({names_before} names before)")
            for annotation in annotations:

                # get affected occurrenceIDs based on name

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

                occurrence_ids = list(df_occurrence.loc[df_occurrence[field] == name]["occurrenceID"])

                # get affected occurrenceIDs based on AphiaID

                if "AphiaID" in annotation:
                    affected_taxon = pyworms.aphiaRecordByAphiaID(str(annotation["AphiaID"]).strip())
                    affected_id = affected_taxon["valid_AphiaID"] if affected_taxon["valid_AphiaID"] is not None else affected_taxon["AphiaID"]
                    occurrence_ids_aphiaid = list(df_occurrence.loc[df_occurrence["valid_AphiaID"].astype(int) == int(affected_id)]["occurrenceID"])
                    occurrence_ids = list(set(occurrence_ids + occurrence_ids_aphiaid))

                # apply

                if annotation["remove"] == True or annotation["remove"] == "true":

                    logging.debug(f"Removing {field} {name} from {site_name}")
                    # TODO: use higher taxon (phylum?) for scientificName and scientificNameID
                    if len(occurrence_ids) > 0:
                        df_occurrence.loc[df_occurrence["occurrenceID"].isin(occurrence_ids), ["class", "order", "family", "genus", "taxonRank"]] = None
                        df_occurrence.loc[df_occurrence["occurrenceID"].isin(occurrence_ids), ["scientificName"]] = "incertae sedis"
                        df_occurrence.loc[df_occurrence["occurrenceID"].isin(occurrence_ids), ["scientificNameID"]] = "urn:lsid:marinespecies.org:taxname:12"
                        df_occurrence.loc[df_occurrence["occurrenceID"].isin(occurrence_ids), ["identificationRemarks"]] = "scientificName changed due to a manual annotation; " + df_occurrence.loc[df_occurrence["occurrenceID"].isin(occurrence_ids), ["identificationRemarks"]]

                if (annotation["remove"] == False or annotation["remove"] == "false") and "new_AphiaID" in annotation:

                    logging.debug(f"Updating {field} {name} for {site_name}")
                    if len(occurrence_ids) > 0:
                        new_taxon = pyworms.aphiaRecordByAphiaID(str(annotation["new_AphiaID"]).strip())
                        df_occurrence.loc[df_occurrence["occurrenceID"].isin(occurrence_ids), ["kingdom"]] = new_taxon["kingdom"]
                        df_occurrence.loc[df_occurrence["occurrenceID"].isin(occurrence_ids), ["phylum"]] = new_taxon["phylum"]
                        df_occurrence.loc[df_occurrence["occurrenceID"].isin(occurrence_ids), ["class"]] = new_taxon["class"]
                        df_occurrence.loc[df_occurrence["occurrenceID"].isin(occurrence_ids), ["order"]] = new_taxon["order"]
                        df_occurrence.loc[df_occurrence["occurrenceID"].isin(occurrence_ids), ["family"]] = new_taxon["family"]
                        df_occurrence.loc[df_occurrence["occurrenceID"].isin(occurrence_ids), ["genus"]] = new_taxon["genus"]
                        df_occurrence.loc[df_occurrence["occurrenceID"].isin(occurrence_ids), ["scientificName"]] = new_taxon["scientificname"]
                        df_occurrence.loc[df_occurrence["occurrenceID"].isin(occurrence_ids), ["scientificNameID"]] = new_taxon["lsid"]
                        df_occurrence.loc[df_occurrence["occurrenceID"].isin(occurrence_ids), ["taxonRank"]] = new_taxon["rank"].lower()
                        df_occurrence.loc[df_occurrence["occurrenceID"].isin(occurrence_ids), ["identificationRemarks"]] = "scientificName changed due to a manual annotation; " + df_occurrence.loc[df_occurrence["occurrenceID"].isin(occurrence_ids), ["identificationRemarks"]]

            names_after = df_occurrence["scientificName"].nunique()
            logging.info(f"{names_after} names after")

        if self.remove_contaminants:

            with open(f"annotations/contaminants.json") as f:
                annotations = json.load(f)
                logging.info(f"Removing {len(annotations)} contamintants for {site_name}")

                for annotation in annotations:
                    for rank, name in annotation.items():
                        logging.debug(f"Removing {rank} {name} from {site_name}")
                        occurrence_ids = list(df_occurrence.loc[df_occurrence[rank.strip()] == name.strip()]["occurrenceID"])
                        df_occurrence = df_occurrence[~df_occurrence["occurrenceID"].isin(occurrence_ids)]

                names_after = df_occurrence["scientificName"].nunique()
                logging.info(f"{names_after} names after")

        return df_occurrence
