import asyncio

from fastapi import APIRouter, UploadFile, File

from app.utils.logger import setup_logger
from app.services.gcloud.gbucketClient import upload_pdf_to_gcloud_bucket
from app.services.gcloud.vertexClient import generate_embeddings_from_vertex
from app.config import PDF_GBUCKET_NAME

from app.main import vespa_client


router = APIRouter()
logger = setup_logger()


@router.post('/generate-stream', dependencies=[])
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
