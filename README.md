# eDNA results :tropical_fish:

This is a workflow for processing eDNA results from the [eDNA Expeditions project](https://www.unesco.org/en/edna-expeditions) into an integrated dataset. Source data are fetched from [pacman-pipeline-results](https://github.com/iobis/pacman-pipeline-results) and [edna-tracker-data](https://github.com/iobis/edna-tracker-data), output is committed to a dedicated branch [data](https://github.com/iobis/edna-results/tree/data/data).

## How to read this dataset

### Download the dataset

Downloadn the zipped dataset from <https://obis-edna-results.s3.amazonaws.com/output.zip>.

### Read the dataset using R

See https://github.com/iobis/edna-results/blob/master/docs/read.md.

## For maintainers

To update the integrated dataset based on new data in [pacman-pipeline-results](https://github.com/iobis/pacman-pipeline-results) or new annotations in this repository, run the workflow in [Actions](https://github.com/iobis/edna-results/actions/workflows/run.yml).
