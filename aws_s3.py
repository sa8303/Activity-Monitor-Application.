import boto3
from botocore.exceptions import NoCredentialsError
import os

# AWS S3 Configuration
AWS_ACCESS_KEY = ''  # Replace with your access key
AWS_SECRET_KEY = ''  # Replace with your secret key
BUCKET_NAME = ''     # Replace with your S3 bucket name
REGION_NAME = ''    # region

def upload_to_s3(file_path, s3_folder=''):
    """
    Uploads a file to S3 bucket.

    :param file_path: Path to the file to be uploaded
    :param s3_folder: Folder in S3 where the file will be uploaded
    :return: True if file was uploaded, else False
    """
    try:
        s3 = boto3.client('s3', 
                          aws_access_key_id=AWS_ACCESS_KEY,
                          aws_secret_access_key=AWS_SECRET_KEY,
                          region_name=REGION_NAME)

        if s3_folder:
            s3_path = os.path.join(s3_folder, os.path.basename(file_path))
        else:
            s3_path = os.path.basename(file_path)

        s3.upload_file(file_path, BUCKET_NAME, s3_path)
        print(f"Upload Successful: {file_path} to {s3_path}")
        return True
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return False
    except NoCredentialsError:
        print("Credentials not available")
        return False
    except Exception as e:
        print(f"Error uploading file: {e}")
        return False
