import base64
import json
import os
import asyncio

from google.cloud import aiplatform
from app.config import (
  VERTEX_ENDPOINT_ID,
  VERTEX_PROJECT_ID,
  VERTEX_LOCATION,
  CACHE_DOC_RESPONSE_FILE_NAME,
  CACHE_QUERY_RESPONSE_FILE_NAME,
  CACHE_DIR_ROOT_PATH,
)

aiplatform.init(
  project=VERTEX_PROJECT_ID,
  location=VERTEX_LOCATION,
)


async def generate_embeddings_from_vertex(
  mode='document', pdf_url=None, query_text=None, use_cache=False, cache_response=False
):
  """
  Generate embeddings asynchronously using the ColQwen2 model on Vertex.
  """
  if mode not in ['document', 'query']:
    raise ValueError("Mode must be either 'document' or 'query'")

  if mode == 'document' and not pdf_url and not use_cache:
    raise ValueError('PDF URL is required in document mode')
  if mode == 'query' and not query_text and not use_cache:
    raise ValueError('Query text is required in query mode')

  cache_files = {
    'document': CACHE_DOC_RESPONSE_FILE_NAME,
    'query': CACHE_QUERY_RESPONSE_FILE_NAME,
  }

  if use_cache:
    try:
      cache_dir = ensure_cache_directory()
      cache_file = os.path.join(cache_dir, cache_files[mode])
      with open(cache_file, 'r') as f:
        return json.load(f)
    except FileNotFoundError:
      print(f'Cache file {cache_files[mode]} not found')
      return None

  async def predict_async(endpoint_id, instances):
    endpoint = aiplatform.Endpoint(endpoint_name=endpoint_id)
    # Execute the call in a separate thread to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, endpoint.predict, instances)
    return response

  endpoint_id = VERTEX_ENDPOINT_ID
  if not endpoint_id:
    raise ValueError('VERTEX_ENDPOINT_ID environment variable is required')

  if mode == 'document':
    instances = [{'pdf_url': pdf_url}]
  else:
    instances = [{'query_text': query_text}]

  response = await predict_async(endpoint_id, instances)
  pages_meta_info = response.predictions[0]

  if cache_response:
    try:
      cache_dir = ensure_cache_directory()
      cache_file = os.path.join(cache_dir, cache_files[mode])
      with open(cache_file, 'w') as f:
        json.dump(pages_meta_info, f)
    except Exception as e:
      print(f'Errore nella scrittura del cache file: {e}')
      print(f'Percorso tentato: {cache_file}')

  return pages_meta_info


def generate_embeddings_from_vertex_noasync(
  mode='document', pdf_url=None, query_text=None, use_cache=False, cache_response=False
):
  """
  Generate embeddings using the ColQwen2 model on Vertex.

  Args:
      mode (str): "document" to process PDF or "query" for query embeddings
      pdf_url (str, optional): URL of the PDF to process
      query_text (str, optional): Text of the query
      use_cache (bool): If True, load example data (cached/saved from previous run)
      cache_response (bool): If True, save the response to a cache file for future use

  Returns:
      Union[list, dict]: Embeddings for documents or queries
  """
  # Check input parameters
  if mode not in ['document', 'query']:
    raise ValueError("Mode must be either 'document' or 'query'")

  if mode == 'document' and not pdf_url and not use_cache:
    raise ValueError('PDF URL is required in document mode')
  if mode == 'query' and not query_text and not use_cache:
    raise ValueError('Query text is required in query mode')

  cache_files = {
    'document': CACHE_DOC_RESPONSE_FILE_NAME,
    'query': CACHE_QUERY_RESPONSE_FILE_NAME,
  }

  # DEV: use_cache if True, load example data
  if use_cache:
    try:
      with open(cache_files[mode], 'r') as f:
        return json.load(f)['output']
    except FileNotFoundError:
      print(f'Cache file {cache_files[mode]} not found')
      use_cache = False  # Fallback to real API call

  #  Vertex Call
  def predict(endpoint_id, instances):
    endpoint = aiplatform.Endpoint(endpoint_name=endpoint_id)
    response = endpoint.predict(instances=instances)
    return response

  endpoint_id = VERTEX_ENDPOINT_ID
  if not endpoint_id:
    raise ValueError('VERTEX_ENDPOINT_ID environment variable is required')

  if mode == 'document':
    instances = [{'pdf_url': pdf_url}]
  else:
    instances = [{'query_text': query_text}]

  response = predict(endpoint_id, instances)

  if cache_response:
    try:
      cache_dir = ensure_cache_directory()
      cache_file = os.path.join(cache_dir, cache_files[mode])
      with open(cache_file, 'w') as f:
        json.dump(response, f)
    except Exception as e:
      print(f'Errore nella scrittura del cache file: {e}')
      print(f'Percorso tentato: {cache_file}')

  return response.predictions[0]


def ensure_cache_directory():
  # Ottieni il percorso base dell'applicazione
  app_dir = os.path.dirname(os.path.abspath(__file__))

  cache_dir_name = CACHE_DIR_ROOT_PATH
  configured_dir = os.path.join(app_dir, cache_dir_name)
  try:
    # Crea la directory se non esiste
    os.makedirs(configured_dir, exist_ok=True)
    return configured_dir

  except (OSError, PermissionError) as e:
    print(f'Directory originale non scrivibile: {e}')
    return None


def image_to_base64(image):
  """
  Converts a PIL image to base64 format.

  This function takes an image in the PIL (Python Imaging Library) format
  and converts it into a base64 string. This format is necessary for
  transmitting images through RESTful APIs.

  Args:
      image: PIL image object

  Returns:
      str: Base64 string representing the image in PNG format
  """
  import io

  buffered = io.BytesIO()
  image.save(buffered, format='PNG')

  return base64.b64encode(buffered.getvalue()).decode('utf-8')
