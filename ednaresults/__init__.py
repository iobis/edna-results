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


class OccurrenceBuilder():

    def __init__(
        self,
        project_names=["eDNAexpeditions_batch1_samples", "eDNAexpeditions_batch2_samples"],
        occurrence_file="Occurrence_table.tsv",
        dna_file="DNA_extension_table.tsv",
        output_folder="output",
        remove_contaminants=True,
        list_generator=None
    ):
        self.project_names = project_names
        self.occurrence_file = occurrence_file
        self.dna_file = dna_file
        self.output_folder = output_folder
        self.remove_contaminants = remove_contaminants
        self.list_generator = list_generator

    def download_results(self) -> None:
        logging.warning(f"Downloading pipeline results to {self.output_folder}\nRemove folder pacman-pipeline-results to force an update")
        if not os.path.exists("pacman-pipeline-results"):
            os.system("git clone --depth 1 https://github.com/iobis/pacman-pipeline-results.git")

    def fetch_metadata(self) -> dict:
        metadata_url = "https://raw.githubusercontent.com/iobis/edna-tracker-data/data/generated.json"
        logging.info(f"Downloading metadata from {metadata_url}")
        with urllib.request.urlopen(metadata_url) as url:
            data = json.load(url)
            return data

    def fetch_metadata_df(self):
        metadata = self.fetch_metadata()

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

        return metadata_df

    def list_datasets(self) -> list:
        datasets = []
        for project_name in self.project_names:
            root_folder = os.path.join("pacman-pipeline-results", project_name, "runs")
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

    def apply_annotations(self, df_occurrence: pd.DataFrame, site_name: str) -> pd.DataFrame:

        with open(f"annotations/{site_name}.json") as f:
            annotations = json.load(f)
            logging.info(f"Applying {len(annotations)} annotations for {site_name}")
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

                    logging.debug(f"Removing {field} {name} from {site_name}")
                    # TODO: use higher taxon (phylum?) for scientificName and scientificNameID
                    occurrence_ids = list(df_occurrence.loc[df_occurrence[field] == name]["occurrenceID"])
                    df_occurrence.loc[df_occurrence["occurrenceID"].isin(occurrence_ids), ["class", "order", "family", "genus", "taxonRank"]] = None
                    df_occurrence.loc[df_occurrence["occurrenceID"].isin(occurrence_ids), ["scientificName"]] = "incertae sedis"
                    df_occurrence.loc[df_occurrence["occurrenceID"].isin(occurrence_ids), ["scientificNameID"]] = "urn:lsid:marinespecies.org:taxname:12"
                    df_occurrence.loc[df_occurrence["occurrenceID"].isin(occurrence_ids), ["identificationRemarks"]] = "scientificName changed due to a manual annotation; " + df_occurrence.loc[df_occurrence["occurrenceID"].isin(occurrence_ids), ["identificationRemarks"]]

                if (annotation["remove"] == False or annotation["remove"] == "false") and "new_AphiaID" in annotation:

                    logging.debug(f"Updating {field} {name} for {site_name}")
                    occurrence_ids = list(df_occurrence.loc[df_occurrence[field] == name]["occurrenceID"])
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

        if self.remove_contaminants:

            with open(f"annotations/contaminants.json") as f:
                annotations = json.load(f)
                logging.info(f"Removing {len(annotations)} contamintants for {site_name}")

                for annotation in annotations:
                    for rank, name in annotation.items():
                        logging.debug(f"Removing {rank} {name} from {site_name}")
                        occurrence_ids = list(df_occurrence.loc[df_occurrence[rank.strip()] == name.strip()]["occurrenceID"])
                        df_occurrence = df_occurrence[~df_occurrence["occurrenceID"].isin(occurrence_ids)]

        return df_occurrence

    def upload(self, bucket_name: str = "obis-edna-results") -> None:

        # compress all files in output folder

        zip_file = "output.zip"
        os.system(f"zip -r output.zip {self.output_folder}")

        # upload zip file to S3

        access_key = os.environ["AWS_ACCESS_KEY_ID"]
        secret_key = os.environ["AWS_SECRET_ACCESS_KEY"]

        s3 = boto3.client("s3", aws_access_key_id=access_key, aws_secret_access_key=secret_key)

        try:
            s3.upload_file(zip_file, bucket_name, zip_file)
            logging.info("Upload Successful")
        except FileNotFoundError:
            logging.error("File not found")
        except NoCredentialsError:
            logging.error("Credentials not available")

    def build(self):

        # download pipeline results from GitHub

        self.download_results()

        # fetch metadata from PlutoF and format

        metadata_df = self.fetch_metadata_df()

        # prepare output folder

        logging.warn(f"Clearing output directory {self.output_folder}")
        shutil.rmtree(self.output_folder)
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)
        if not os.path.exists(os.path.join(self.output_folder, "blank")):
            os.makedirs(os.path.join(self.output_folder, "blank"))

        # process by site

        folders_by_site = self.get_folders_by_site()

        for site_name in folders_by_site:

            logging.info(f"Processing {site_name} data")

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

            # concat

            if len(occurrence_tables) != len(dna_tables) or len(occurrence_tables) == 0:
                logging.warn(f"Skipping {site_name} due to missing data")
                continue

            occurrence_combined = pd.concat(occurrence_tables)
            dna_combined = pd.concat(dna_tables)

            # replace sample ID EE0476 with EE0475

            occurrence_combined["occurrenceID"] = occurrence_combined["occurrenceID"].str.replace("EE0476", "EE0475")
            occurrence_combined["materialSampleID"] = occurrence_combined["materialSampleID"].str.replace("EE0476", "EE0475")
            dna_combined["occurrenceID"] = dna_combined["occurrenceID"].str.replace("EE0476", "EE0475")

            # merge metadata, split blanks

            metadata_df_blank = metadata_df[metadata_df["blank"] == True]
            metadata_df_notblank = metadata_df[metadata_df["blank"] == False]

            occurrence_combined_blank = pd.merge(occurrence_combined, metadata_df_blank, on="materialSampleID", how="inner")
            occurrence_combined_notblank = pd.merge(occurrence_combined, metadata_df_notblank, on="materialSampleID", how="inner")

            # apply annotations

            occurrence_combined_notblank = self.apply_annotations(occurrence_combined_notblank, site_name)

            # cleanup dna tables

            occurrence_ids_blank = list(occurrence_combined_blank["occurrenceID"])
            occurrence_ids_notblank = list(occurrence_combined_notblank["occurrenceID"])

            dna_combined_blank = dna_combined[dna_combined["occurrenceID"].isin(occurrence_ids_blank)]
            dna_combined_notblank = dna_combined[dna_combined["occurrenceID"].isin(occurrence_ids_notblank)]

            # output

            occurrence_combined_blank.to_csv(os.path.join(self.output_folder, "blank", f"{site_name}_Occurrence.tsv"), sep="\t", index=False)
            dna_combined_blank.to_csv(os.path.join(self.output_folder, "blank", f"{site_name}_DNADerivedData.tsv"), sep="\t", index=False)

            occurrence_combined_notblank.to_csv(os.path.join(self.output_folder, f"{site_name}_Occurrence.tsv"), sep="\t", index=False)
            dna_combined_notblank.to_csv(os.path.join(self.output_folder, f"{site_name}_DNADerivedData.tsv"), sep="\t", index=False)

            # species lists

            if self.list_generator is not None:
                self.list_generator.run(site_name, occurrence_combined_notblank, dna_combined_notblank, metadata_df_notblank)
