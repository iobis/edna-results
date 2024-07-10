import pandas as pd
from retry_requests import retry
from requests import Session


retry_session = retry(Session(), retries=5, backoff_factor=2)


def split_max_n(lst: list, n: int) -> list[list]:
    return [lst[i * n:(i + 1) * n] for i in range((len(lst) + n - 1) // n)]


def add_accepted_aphiaid(df: pd.DataFrame) -> pd.DataFrame:
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
            "phylum": record["phylum"],
            "class": record["class"],
            "order": record["order"],
            "family": record["family"],
            "genus": record["genus"],
            "species": record["scientificname"],
            "marine": record["isMarine"] != 0 or record["isBrackish"] != 0,
            "rank": record["rank"]
        } for record in aphia_records]
        assert len(records) == len(batch)
        taxa.extend(records)
    taxa_df = pd.DataFrame(taxa)
    df = pd.concat([df, taxa_df], axis=1)

    return df
