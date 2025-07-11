import os
from dotenv import load_dotenv

load_dotenv()

# REQUIRED_VARIABLES = [
# ]

# Vertex AI Config
VERTEX_PROJECT_ID = os.environ['VERTEX_PROJECT_ID']
VERTEX_LOCATION = os.environ['VERTEX_LOCATION']
VERTEX_ENDPOINT_ID = os.environ['VERTEX_ENDPOINT_ID']

# Google Bucket Config
PDF_GBUCKET_NAME = os.environ['PDF_GBUCKET_NAME']

# Cache Config
CACHE_DOC_RESPONSE_FILE_NAME = os.environ['CACHE_DOC_RESPONSE_FILE_NAME']
CACHE_QUERY_RESPONSE_FILE_NAME = os.environ['CACHE_QUERY_RESPONSE_FILE_NAME']
CACHE_DIR_ROOT_PATH = os.environ['CACHE_DIR_ROOT_PATH']

# Logger Config
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'info')

# Vespa Config
VESPA_TENANT_NAME = os.environ['VESPA_TENANT_NAME']
VESPA_APP_NAME = os.environ['VESPA_APP_NAME']
VESPA_ENDPOINT = os.environ.get('VESPA_ENDPOINT', None)
VESPA_CLOUD_SECRET_TOKEN = os.environ['VESPA_CLOUD_TOKEN']
VESPA_KEY_FILENAME = os.environ['VESPA_KEY_FILENAME']
VESPA_APP_PACKAGE_NAME = os.environ['VESPA_APP_PACKAGE_NAME']
