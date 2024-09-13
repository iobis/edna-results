# eDNA results :tropical_fish:

This is a workflow for processing eDNA results from the [eDNA Expeditions project](https://www.unesco.org/en/edna-expeditions) into an integrated dataset. Source data are fetched from AWS and [edna-tracker-data](https://github.com/iobis/edna-tracker-data).

Steps:

- Fetch metadata from GitHub
- Fetch pipeline results from AWS
- Combine data by site
- WoRMS matching and taxonomy replacement
- Separate blanks data
- Apply annotations (remove or update names)
- Generate WoRMS aligned species lists and statistics
- Upload results to AWS

## How to use this dataset
### Download the dataset

Download the zipped dataset from <https://obis-edna-results.s3.amazonaws.com/output.zip> and extract.

```bash
rm -r output output.zip
wget https://obis-edna-results.s3.amazonaws.com/output.zip
unzip output.zip
```

### Read the dataset using R

See https://github.com/iobis/edna-results/blob/master/docs/read.md.

### Access species lists

This package also outputs species lists, download from <https://obis-edna-lists.s3.amazonaws.com/output_lists.zip> or browse the lists [here](https://obis-edna-lists.s3.amazonaws.com/index.html).
