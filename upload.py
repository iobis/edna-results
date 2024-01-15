import os
import boto3
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv


OUPUT_FOLDER = "output"
BUCKET_NAME = "obis-edna-results"


load_dotenv()


# compress all files in output folder

zip_file = f"{OUPUT_FOLDER}.zip"
os.system(f"zip -r {OUPUT_FOLDER}.zip {OUPUT_FOLDER}")

# upload zip file to S3

ACCESS_KEY = os.environ["AWS_ACCESS_KEY_ID"]
SECRET_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]

s3 = boto3.client("s3", aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY)

try:
    response = s3.upload_file(zip_file, BUCKET_NAME, zip_file)
    print("Upload Successful")
except FileNotFoundError:
    print("File not found")
except NoCredentialsError:
    print("Credentials not available")
