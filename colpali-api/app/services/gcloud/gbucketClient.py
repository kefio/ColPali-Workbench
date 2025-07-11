from google.cloud import storage
from io import BytesIO


def upload_pdf_to_gcloud_bucket(bucket_name: str, file_contents: bytes, destination_blob_name: str):
  """Uploads a file to the bucket, creating the bucket if it doesn't exist, and makes it public."""

  storage_client = storage.Client()
  bucket = storage_client.bucket(bucket_name)

  if not bucket.exists():
    bucket = storage_client.create_bucket(bucket_name)

  blob = bucket.blob(destination_blob_name)
  blob.upload_from_file(BytesIO(file_contents), content_type='application/pdf')

  blob.make_public()

  pdf_uploaded_url = f'https://storage.googleapis.com/{bucket_name}/{destination_blob_name}'

  return pdf_uploaded_url
