import pandas as pd
import requests
from ednaresults.aphia import add_accepted_aphiaid, add_taxonomy
import os
import datetime
import simplejson as json
import logging
import csv
from pandas.api.types import is_numeric_dtype
import shutil


class ListGenerator:

    def __init__(self):
        self.output_folder = "output_lists"

    def prepare_output_folder(self):
        logging.warn(f"Clearing output directory {self.output_folder}")
        shutil.rmtree(self.output_folder, ignore_errors=True)
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

        subfolders = [
            os.path.join(self.output_folder, "lists_full", "csv"),
            os.path.join(self.output_folder, "lists", "csv"),
            os.path.join(self.output_folder, "lists_full", "json"),
            os.path.join(self.output_folder, "lists", "json")
        ]

        for subfolder in subfolders:
            os.makedirs(subfolder)

    def fetch_database_species(self, site_name):
        url = f"https://raw.githubusercontent.com/iobis/mwhs-obis-species/master/lists/{site_name}.json"
        res = requests.get(url)
        species = pd.DataFrame(res.json()["species"])[["species", "AphiaID", "records", "obis", "gbif", "max_year"]]
        species = species.rename(columns={
            "species": "scientificName",
            "obis": "source_obis",
            "gbif": "source_gbif"
        })
        species["records"] = species["records"].astype("Int64")
        return species

    def clean_json_records(self, records):
        return [{k: record[k] for k in record if not pd.isna(record[k])} for record in records]

    def run(self, site_name, occurrence, dna, metadata):

        # get dna species (non blank)

        occurrence_species = occurrence[(occurrence["taxonRank"] == "species") & (occurrence["blank"].notna())][["materialSampleID", "occurrenceID", "scientificName", "scientificNameID", "organismQuantity"]]
        dna = dna[["occurrenceID", "target_gene"]]
        df = pd.merge(occurrence_species, dna, on="occurrenceID", how="inner")
        df["AphiaID"] = df.scientificNameID.str.extract("(\d+)")
        edna_species = df.groupby(["scientificName", "AphiaID"]) \
            .agg(
                reads=("organismQuantity", "sum"),
                target_gene=("target_gene", lambda x: ",".join(set(x))),
                asvs=("occurrenceID", "count")
            ).reset_index()

        edna_species_accepted = add_accepted_aphiaid(edna_species)
        edna_species_accepted["source_dna"] = True

        # get obis species

        database_species = self.fetch_database_species(site_name)
        database_species_accepted = add_accepted_aphiaid(database_species)

        # combine

        combined = pd.concat([edna_species_accepted, database_species_accepted], axis=0)
        aggregated = combined.groupby(["valid_AphiaID"]).agg({
            "source_dna": "max",
            "source_obis": "max",
            "source_gbif": "max",
            "records": "first",
            "target_gene": "first",
            "reads": "first",
            "asvs": "first",
            "max_year": "first"
        }).reset_index()
        aggregated.fillna(value={
            "source_dna": False,
            "source_obis": False,
            "source_gbif": False
        }, inplace=True)

        # add taxonomy

        aggregated = add_taxonomy(aggregated)
        # todo: remove using annotation utilities
        aggregated = aggregated[aggregated["species"] != "Homo sapiens"]
        aggregated = aggregated.drop("valid_AphiaID", axis=1)

        # add red list

        redlist = pd.read_csv("supporting_data/redlist.csv")
        redlist = redlist[redlist["category"].isin(["CR", "EN", "EW", "EX", "VU"])]
        aggregated = pd.merge(aggregated, redlist, how="left", on="species")

        # add vernacular

        vernacular = pd.read_csv("supporting_data/vernacularname.txt", sep="\t")
        vernacular = vernacular[vernacular["language"] == "ENG"]
        # vernacular["AphiaID"] = vernacular.taxonID.str.extract("(\d+)")
        vernacular = vernacular.rename(columns={"taxonID": "AphiaID"})
        assert is_numeric_dtype(vernacular["AphiaID"])
        vernacular = vernacular.groupby(["AphiaID"])["vernacularName"].apply(",".join).reset_index()
        vernacular["AphiaID"] = vernacular["AphiaID"].astype(int)
        aggregated = pd.merge(aggregated, vernacular, how="left", on="AphiaID")

        # add group

        groups = pd.read_csv("supporting_data/groups.csv")
        aggregated["group"] = pd.Series(dtype="string")
        for index, row in groups.iterrows():
            aggregated.loc[aggregated[row["rank"]] == row["taxon"], "group"] = row["group"]

        # TODO: fix for subspecies/forma/variety

        aggregated = aggregated[aggregated["rank"] == "Species"]

        # fixes

        aggregated["records"] = aggregated["records"].astype("Int64")
        aggregated["reads"] = aggregated["reads"].astype("Int64")
        aggregated["asvs"] = aggregated["asvs"].astype("Int64")
        aggregated["max_year"] = aggregated["max_year"].astype("Int64")

        aggregated = aggregated.rename(columns={"category": "redlist_category", "vernacularName": "vernacular"})
        aggregated = aggregated.sort_values(by=["group", "phylum", "class", "order", "species"])
        aggregated = aggregated.filter(["AphiaID", "phylum", "class", "order", "family", "genus", "species", "records", "reads", "asvs", "max_year", "target_gene", "source_obis", "source_gbif", "source_dna", "category", "redlist_category", "vernacular", "group"])

        aggregated_dna = aggregated[aggregated["source_dna"]]

        # stats redlist

        stats_redlist = aggregated_dna.groupby("redlist_category").agg({
            "source_obis": "sum",
            "source_gbif": "sum",
            "source_dna": "sum"
        }).reset_index().rename({
            "redlist_category": "category",
            "source_obis": "obis_species",
            "source_gbif": "gbif_species",
            "source_dna": "edna_species"
        }, axis=1).to_dict(orient="records")

        stats_edna_groups = aggregated_dna.groupby("group").size().to_dict()

        # stats sources

        aggregated_for_stats = aggregated_dna.filter(["AphiaID", "source_obis", "source_gbif", "source_dna"])
        aggregated_for_stats["db"] = aggregated_for_stats["source_obis"] | aggregated_for_stats["source_gbif"]
        aggregated_for_stats["both"] = aggregated_for_stats["db"] & aggregated_for_stats["source_dna"]
        aggregated_for_stats = aggregated_for_stats.rename({
            "source_obis": "obis",
            "source_gbif": "gbif",
            "source_dna": "edna",
        }, axis=1)
        stats_sources = aggregated_for_stats.agg({
            "obis": "sum",
            "gbif": "sum",
            "edna": "sum",
            "db": "sum",
            "both": "sum"
        }).to_dict()

        # stats samples
        # TODO: accepted species only

        sample_species_stats = occurrence_species.groupby("materialSampleID").agg({
            "scientificName": "nunique"
        }).rename({"scientificName": "species"}, axis=1).reset_index()

        stats_samples = occurrence.groupby(["materialSampleID"]) \
            .agg(
                reads=("organismQuantity", "sum"),
                asvs=("occurrenceID", "count")
            ) \
            .reset_index() \
            .merge(metadata, on="materialSampleID", how="left") \
            .merge(sample_species_stats, on="materialSampleID", how="left") \
            .to_dict(orient="records")

        # output

        csv_full_path = os.path.join(self.output_folder, "lists_full", "csv", f"{site_name}.csv")
        csv_dna_path = os.path.join(self.output_folder, "lists", "csv", f"{site_name}.csv")
        json_full_path = os.path.join(self.output_folder, "lists_full", "json", f"{site_name}.json")
        json_dna_path = os.path.join(self.output_folder, "lists", "json", f"{site_name}.json")

        logging.info(f"Writing {csv_full_path}")
        aggregated.to_csv(csv_full_path, index=False, quoting=csv.QUOTE_NONNUMERIC)

        logging.info(f"Writing {csv_dna_path}")
        aggregated[aggregated["source_dna"]].to_csv(csv_dna_path, index=False, quoting=csv.QUOTE_NONNUMERIC)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        json_full = {
            "created": timestamp,
            "species": self.clean_json_records(aggregated.to_dict(orient="records")),
            "stats": {
                "redlist": stats_redlist,
                "groups_edna": stats_edna_groups,
                "source": stats_sources,
                "samples": stats_samples
            }
        }
        json_dna = {
            "created": timestamp,
            "species": self.clean_json_records(aggregated_dna.to_dict(orient="records")),
            "stats": {
                "redlist": stats_redlist,
                "groups_edna": stats_edna_groups,
                "source": stats_sources,
                "samples": stats_samples
            }
        }
        logging.info(f"Writing {json_full_path}")
        with open(json_full_path, "w") as file:
            file.write(json.dumps(json_full, indent=2, ignore_nan=True))
        logging.info(f"Writing {json_dna_path}")
        with open(json_dna_path, "w") as file:
            file.write(json.dumps(json_dna, indent=2, ignore_nan=True))
