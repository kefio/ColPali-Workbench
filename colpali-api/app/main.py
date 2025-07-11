import asyncio
import json
import time

import base64
import torch
from contextlib import asynccontextmanager

from fastapi import Body, FastAPI, UploadFile, File, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.vespa.vespaClient import VespaClient
from app.services.gcloud.vertexClient import generate_embeddings_from_vertex
from app.services.gcloud.gbucketClient import upload_pdf_to_gcloud_bucket
from app.services.gcloud.llamaClient import generate_response_from_llama

from app.config import PDF_GBUCKET_NAME
from app.utils.logger import setup_logger

logger = setup_logger()

vespa_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
  global vespa_client
  logger.info('Application starting up')
  try:
    vespa_client = VespaClient()
    logger.info('Vespa client initialized successfully')
    yield
  except Exception as e:
    logger.error(f'Error during application startup: {str(e)}')
    yield
  finally:
    logger.info('Application shutting down')


app = FastAPI(lifespan=lifespan)


class LoggingMiddleware(BaseHTTPMiddleware):
  async def dispatch(self, request: Request, call_next):
    start_time = time.time()
    try:
      response = await call_next(request)
      process_time = time.time() - start_time

      logger.info(
        'Request handled successfully',
        extra={
          'method': request.method,
          'url': request.url,
          'status_code': response.status_code,
          'process_time': process_time,
        },
      )
      return response
    except Exception as exc:
      process_time = time.time() - start_time
      try:
        body_bytes = await request.body()
        body_str = body_bytes.decode('utf-8')
        body = json.loads(body_str)
      except Exception:
        body = None

      logger.error(
        'Request failed',
        exc_info=True,
        extra={
          'method': request.method,
          'url': request.url,
          'process_time': process_time,
          'query_params': request.query_params,
          'path_params': request.path_params,
          'body': body,
          'exception': str(exc),
        },
      )

      response = Response('Internal Server Error', status_code=500)
      return response


app.add_middleware(
  CORSMiddleware,
  allow_origins=['*'],  # Allow all origins
  allow_credentials=True,
  allow_methods=['*'],
  allow_headers=['*'],
)

app.add_middleware(LoggingMiddleware)

# app.include_router(router, prefix='/api')


# TODO remove
@app.post('/deploy')
async def deploy():
  global vespa_client
  try:
    vespa_client = VespaClient()
    logger.info('Vespa client initialized.')
    return {'status': 'success', 'message': 'Vespa client initialized.'}
  except Exception as e:
    logger.error(f'Error initializing Vespa client: {str(e)}')
    return {'status': 'error', 'message': 'Error initializing Vespa client.'}


@app.post('/pdf')
async def process_pdf(file: UploadFile = File(...)):
  bucket_name = PDF_GBUCKET_NAME
  destination_blob_name = file.filename
  logger.info(f'Received file: {file.filename}')
  try:
    contents = await file.read()
    logger.info(f'Read file contents for: {file.filename}')

    pdf_uploaded_url = upload_pdf_to_gcloud_bucket(bucket_name, contents, destination_blob_name)

    logger.info(f'Uploaded file to GCloud bucket: {pdf_uploaded_url}')

    page_met_info = await asyncio.wait_for(
      generate_embeddings_from_vertex(
        mode='document',
        pdf_url=pdf_uploaded_url,
        # cache_response=True, ### Used to cache the response from the model for future testing
        # use_cache=True, ### Used to use a previously cached response without calling the model
      ),
      timeout=300,
    )
    logger.info(f'Generated embeddings for document: {pdf_uploaded_url}')

    vespa_feed = vespa_client.build_vespa_feed(page_met_info)
    logger.info(f'Built Vespa feed for document: {pdf_uploaded_url}')

    await vespa_client.feed_data(vespa_feed)
    logger.info(f'Fed data to Vespa for document: {pdf_uploaded_url}')

    return {'success': page_met_info, 'url': pdf_uploaded_url}
  except asyncio.TimeoutError:
    logger.warning(f'Processing timeout for document: {pdf_uploaded_url}')
    return {
      'status': 'processing',
      'message': 'Processing is ongoing but requires more time. Check the status later.',
      'url': pdf_uploaded_url,
    }
  except Exception as e:
    logger.error(f'Error processing document: {pdf_uploaded_url}, Error: {str(e)}')
    return {'error': str(e)}


@app.post('/search')
async def search(query: str = Body(...)):
  logger.info(f'Received search query: {query}')
  try:
    query_response = await asyncio.wait_for(
      generate_embeddings_from_vertex(
        mode='query',
        query_text=query,
        use_cache=True,
      ),
      timeout=300,
    )
    logger.info(f'Generated embeddings for query: {query}')

    query_embeddings = torch.tensor(query_response['embeddings'][0])
    logger.info(f'Query embeddings: {query_embeddings}')

    response = await vespa_client.query(query, query_embeddings)
    logger.info(f'Vespa query response: {response}')

    results = []
    for hit in response.hits:
      results.append(
        {
          'title': hit['fields']['title'],
          'url': hit['fields']['url'],
          'page': hit['fields']['page_number'],
          'score': hit['relevance'],
          'image': hit['fields']['image'],
        }
      )
    logger.info('Generating llama response')

    image_bytes = base64.b64decode(response.hits[0]['fields']['image'])
    image = base64.b64encode(image_bytes).decode('utf-8')

    llama_response = await generate_response_from_llama(image, query)

    return {'query': query, 'results': results, 'llama_response': llama_response}
  except asyncio.TimeoutError:
    logger.warning(f'Search processing timeout for query: {query}')
    return {
      'status': 'processing',
      'message': 'Processing is ongoing but requires more time. Check the status later.',
    }
  except Exception as e:
    logger.error(f'Error processing search query: {query}, Error: {str(e)}')
    return {'error': str(e)}


@app.get('/logs')
def get_logs():
  try:
    with open('app.log', 'r') as log_file:
      logs = log_file.readlines()
    return {'logs': logs}
  except FileNotFoundError:
    return {'error': 'Log file not found.'}
  except Exception as e:
    return {'error': str(e)}


@app.delete('/clear_logs')
def clear_logs():
  try:
    open('app.log', 'w').close()
    logger.info('All logs have been cleared.')
    return {'status': 'success', 'message': 'All logs have been cleared.'}
  except Exception as e:
    logger.error(f'Error clearing logs: {str(e)}')
    return {'status': 'error', 'message': 'Error clearing logs.'}
