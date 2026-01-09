rsync -r ubuntu@lfw-ds001-i035.i.lifewatch.dev:/home/ubuntu/data/dev/PacMAN-pipeline/results/eDNAexpeditions_batch2_samples ./pipeline_data/

aws s3 sync s3://obis-backups/edna_expeditions/pipeline_results/20240606/ ./pipeline_data_20240606/ --exclude "*" --include "eDNAexpeditions_batch*/Scandola*"

aws s3 sync s3://obis-backups/edna_expeditions/pipeline_results/20260107/ /Volumes/acasis/pipeline_data_20260107/