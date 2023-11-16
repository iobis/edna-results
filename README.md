# eDNA results :tropical_fish:

This is a workflow for processing eDNA results from the [eDNA Expeditions project](https://www.unesco.org/en/edna-expeditions) into an integrated dataset. Source data are fetched from [pacman-pipeline-results](https://github.com/iobis/pacman-pipeline-results) and [edna-tracker-data](https://github.com/iobis/edna-tracker-data), output is committed to a dedicated branch [data](https://github.com/iobis/edna-results/tree/data/data).

## How to read this dataset

### Read the dataset using R

```r
library(purrr)
library(dplyr)

system("git clone -b data --depth=1 https://github.com/iobis/edna-results.git")

occurrence_files <- list.files("edna-results/data", "*Occurrence*", full.names = TRUE)
dna_files <- list.files("edna-results/data", "*DNADerivedData*", full.names = TRUE)

occurrence <- map(occurrence_files, read.table, sep = "\t", quote = "", header = TRUE) %>%
  bind_rows() %>%
  mutate_if(is.character, na_if, "")

dna <- map(dna_files, read.table, sep = "\t", quote = "", header = TRUE) %>%
  bind_rows() %>%
  mutate_if(is.character, na_if, "")
```