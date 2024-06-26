import os
import boto3
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv


load_dotenv()
ACCESS_KEY = os.environ["AWS_ACCESS_KEY_ID"]
SECRET_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]


def upload_results():

    OUPUT_FOLDER = "output"
    BUCKET_NAME = "obis-edna-results"

    # compress all files in output folder

    zip_file = f"{OUPUT_FOLDER}.zip"
    os.system(f"zip -r {OUPUT_FOLDER}.zip {OUPUT_FOLDER}")

    # upload zip file to S3

    s3 = boto3.client("s3", aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY)

    try:
        s3.upload_file(zip_file, BUCKET_NAME, zip_file)
        print("Upload Successful")
    except FileNotFoundError:
        print("File not found")
    except NoCredentialsError:
        print("Credentials not available")


def upload_lists():

    OUPUT_FOLDER = "output_lists"
    BUCKET_NAME = "obis-edna-lists"

    # compress all files in output folder

    zip_file = f"{OUPUT_FOLDER}.zip"
    os.system(f"zip -r {OUPUT_FOLDER}.zip {OUPUT_FOLDER}")

    # upload zip file to S3

    s3 = boto3.client("s3", aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY)

    try:
        s3.upload_file(zip_file, BUCKET_NAME, zip_file)
        print("Upload Successful")
    except FileNotFoundError:
        print("File not found")
    except NoCredentialsError:
        print("Credentials not available")

    # upload files to S3

    for root, dirs, files in os.walk(OUPUT_FOLDER):

        for filename in files:
            if filename.endswith(".csv") or filename.endswith(".json"):
                local_path = os.path.join(root, filename)
                relative_path = os.path.relpath(local_path, OUPUT_FOLDER)
                print(f"Uploading {local_path} to {relative_path}")
                try:
                    s3.upload_file(local_path, BUCKET_NAME, relative_path)
                    print("Upload Successful")
                except FileNotFoundError:
                    print("File not found")
                except NoCredentialsError:
                    print("Credentials not available")


upload_results()
upload_lists()
