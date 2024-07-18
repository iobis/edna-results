import pandas as pd
from retry_requests import retry
from requests import Session


retry_session = retry(Session(), retries=5, backoff_factor=2)


def split_max_n(lst: list, n: int) -> list[list]:
    return [lst[i * n:(i + 1) * n] for i in range((len(lst) + n - 1) // n)]


def get_lowest_level_id(row, columns, names_map):
    for col in reversed(columns):
        if pd.notna(row[col]) and row[col] in names_map:
            return names_map[row[col]]
    return None


def add_aphiaid(df: pd.DataFrame) -> pd.DataFrame:
    """Add an AphiaID column to a dataframe with Darwin Core taxonomy terms. The AphiaID for the lowest rank that could be matched is added.
    If no match is found, the AphiaID is set to 12 (unknown)."""

    columns = [col for col in ["phylum", "class", "order", "family", "genus", "scientificName"] if col in df.columns]
    all_names = df[columns].values.ravel()
    distinct_names = pd.unique(all_names[~pd.isna(all_names)])

    batches = split_max_n(distinct_names, 50)
    names_map = {}

    for batch in batches:
        url = "https://www.marinespecies.org/rest/AphiaRecordsByMatchNames?marine_only=false&" + "&".join([f"scientificnames%5B%5D={name}" for name in batch])
        res = retry_session.get(url)
        res.raise_for_status()
        if res.status_code == 204:
            continue
        aphia_records = res.json()

        for i in range(len(batch)):
            for record in aphia_records[i]:
                if record["match_type"].startswith("exact"):
                    names_map[batch[i]] = record["AphiaID"]
                    break

    df["AphiaID"] = df.apply(get_lowest_level_id, axis=1, columns=columns, names_map=names_map)
    df["AphiaID"] = df["AphiaID"].fillna(12).astype(int)

    return df


def add_accepted_aphiaid(df: pd.DataFrame) -> pd.DataFrame:
    """Add a valid_AphiaID column to a dataframe with AphiaIDs."""

    aphiaids = list(df["AphiaID"])
    batches = split_max_n(aphiaids, 50)

    accepted_aphiaids = []

    for batch in batches:
        url = "https://www.marinespecies.org/rest/AphiaRecordsByAphiaIDs?" + "&".join([f"aphiaids%5B%5D={aphiaid}" for aphiaid in batch])
        res = retry_session.get(url)
        res.raise_for_status()
        aphia_records = res.json()
        ids = [str(record["valid_AphiaID"]) if record["valid_AphiaID"] is not None else None for record in aphia_records]
        accepted_aphiaids.extend(ids)

    assert len(accepted_aphiaids) == len(aphiaids)
    df["valid_AphiaID"] = accepted_aphiaids
    df["valid_AphiaID"] = df["valid_AphiaID"].fillna(df["AphiaID"])

    return df


def add_taxonomy(df: pd.DataFrame) -> pd.DataFrame:

    aphiaids = list(df["valid_AphiaID"])
    batches = split_max_n(aphiaids, 50)

    taxa = []

    for batch in batches:
        url = "https://www.marinespecies.org/rest/AphiaRecordsByAphiaIDs?" + "&".join([f"aphiaids%5B%5D={aphiaid}" for aphiaid in batch])
        res = retry_session.get(url)
        res.raise_for_status()
        aphia_records = res.json()
        records = [{
            "AphiaID": record["AphiaID"],
            "kingdom": record["kingdom"],
            "phylum": record["phylum"],
            "class": record["class"],
            "order": record["order"],
            "family": record["family"],
            "genus": record["genus"],
            "species": record["scientificname"],
            "marine": record["isMarine"] != 0 or record["isBrackish"] != 0,
            "rank": record["rank"].lower()
        } for record in aphia_records]
        assert len(records) == len(batch)
        taxa.extend(records)
    taxa_df = pd.DataFrame(taxa)
    df = pd.concat([df, taxa_df], axis=1)

    return df


def add_taxonomy_dwc(df: pd.DataFrame) -> pd.DataFrame:
    """Remove existing taxonomy columns and add taxonomy based on valid_AphiaID."""

    df = df.drop([col for col in ["kingdom", "phylum", "class", "order", "family", "genus", "scientificName", "taxonRank", "AphiaID"] if col in df.columns], axis=1)

    aphiaids = list(df["valid_AphiaID"])
    batches = split_max_n(aphiaids, 50)

    taxa = []

    for batch in batches:
        url = "https://www.marinespecies.org/rest/AphiaRecordsByAphiaIDs?" + "&".join([f"aphiaids%5B%5D={aphiaid}" for aphiaid in batch])
        res = retry_session.get(url)
        res.raise_for_status()
        aphia_records = res.json()
        records = [{
            "AphiaID": record["AphiaID"],
            "kingdom": record["kingdom"],
            "phylum": record["phylum"],
            "class": record["class"],
            "order": record["order"],
            "family": record["family"],
            "genus": record["genus"],
            "scientificName": record["scientificname"],
            "taxonRank": record["rank"].lower()
        } for record in aphia_records]
        assert len(records) == len(batch)
        taxa.extend(records)

    taxa_df = pd.DataFrame(taxa)
    df = pd.concat([df, taxa_df], axis=1)

    return df
