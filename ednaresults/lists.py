import pandas as pd
import requests
from ednaresults.aphia import add_accepted_aphiaid, add_taxonomy
import os
import datetime
import simplejson as json
import logging
import csv


class ListGenerator:

    def __init__(self):
        pass

    def fetch_database_species(self, site_name):
        url = f"https://raw.githubusercontent.com/iobis/mwhs-obis-species/master/lists/{site_name}.json"
        res = requests.get(url)
        species = pd.DataFrame(res.json()["species"])[["species", "AphiaID", "records", "obis", "gbif", "max_year"]]
        species.rename(columns={
            "species": "scientificName",
            "obis": "source_obis",
            "gbif": "source_gbif"
        }, inplace=True)
        species["records"] = species["records"].astype("Int64")
        return species

    def clean_json_records(self, records):
        return [{k: record[k] for k in record if not pd.isna(record[k])} for record in records]

    def run(self, site_name, occurrence, dna):

        # get dna species (non blank)

        occurrence = occurrence[(occurrence["taxonRank"] == "species") & (occurrence["blank"].notna())][["occurrenceID", "scientificName", "scientificNameID", "organismQuantity"]]
        dna = dna[["occurrenceID", "target_gene"]]
        df = pd.merge(occurrence, dna, on="occurrenceID", how="inner")
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
        vernacular["AphiaID"] = vernacular.taxonID.str.extract("(\d+)")
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

        # output

        aggregated["records"] = aggregated["records"].astype("Int64")
        aggregated["reads"] = aggregated["reads"].astype("Int64")
        aggregated["asvs"] = aggregated["asvs"].astype("Int64")
        aggregated["max_year"] = aggregated["max_year"].astype("Int64")

        aggregated.rename(columns={"category": "redlist_category", "vernacularName": "vernacular"})
        aggregated = aggregated.sort_values(by=["group", "phylum", "class", "order", "species"])
        aggregated = aggregated.filter(["AphiaID", "phylum", "class", "order", "family", "genus", "species", "records", "reads", "asvs", "max_year", "target_gene", "source_obis", "source_gbif", "source_dna", "category", "redlist_category", "vernacular", "group"])

        csv_full_path = os.path.join(f"output_lists", "lists_full", "csv", f"{site_name}.csv")
        csv_dna_path = os.path.join(f"output_lists", "lists", "csv", f"{site_name}.csv")
        json_full_path = os.path.join(f"output_lists", "lists_full", "json", f"{site_name}.json")
        json_dna_path = os.path.join(f"output_lists", "lists", "json", f"{site_name}.json")

        logging.info(f"Writing {csv_full_path}")
        aggregated.to_csv(csv_full_path, index=False, quoting=csv.QUOTE_NONNUMERIC)

        logging.info(f"Writing {csv_dna_path}")
        aggregated[aggregated["source_dna"]].to_csv(csv_dna_path, index=False, quoting=csv.QUOTE_NONNUMERIC)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        json_full = {
            "created": timestamp,
            "species": self.clean_json_records(aggregated.to_dict(orient="records"))
        }
        json_dna = {
            "created": timestamp,
            "species": self.clean_json_records(aggregated[aggregated["source_dna"]].to_dict(orient="records"))
        }
        logging.info(f"Writing {json_full_path}")
        with open(json_full_path, "w") as file:
            file.write(json.dumps(json_full, indent=2, ignore_nan=True))
        logging.info(f"Writing {json_dna_path}")
        with open(json_dna_path, "w") as file:
            file.write(json.dumps(json_dna, indent=2, ignore_nan=True))
