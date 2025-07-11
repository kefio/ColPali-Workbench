import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

# Logging configuration
logging.basicConfig(level=logging.INFO)

# Standard paths for Vertex AI
AIP_HEALTH_ROUTE = os.environ.get('AIP_HEALTH_ROUTE', '/health')
AIP_PREDICT_ROUTE = os.environ.get('AIP_PREDICT_ROUTE', '/predict')

app = FastAPI()
predictor = None


# Model for Vertex AI format
class PredictRequest(BaseModel):
  instances: List[Dict[str, Any]]


@app.on_event('startup')
async def startup_event():
  """Startup event to initialize the model"""
  global predictor
  try:
    from app.utils.predictor import Predictor  # Import only when the server starts

    predictor = Predictor()
    predictor.setup()
    logging.info('✅ Predictor initialized successfully!')
  except Exception as e:
    logging.error(f'❌ Error during predictor initialization: {e}')
    raise RuntimeError('Error during model initialization')


@app.get(AIP_HEALTH_ROUTE)
async def health():
  """Health check endpoint"""
  logging.info('✅ Health check received')
  return {'status': 'ok'}


@app.post(AIP_PREDICT_ROUTE)
async def predict(request: PredictRequest):
  """
  Main prediction endpoint for Vertex AI
  - Supports queries (query_text) and documents (pdf_url).
  """

  logging.info(f'📥 Request received: {request.dict()}')

  try:
    # Verify that the request has at least one instance
    if not request.instances or not isinstance(request.instances, list):
      raise HTTPException(
        status_code=400,
        detail="Invalid request format: 'instances' is required",
      )

    # Take the first instance
    instance = request.instances[0]

    # Determine the type of request (the endpoint can receive either a query or a PDF URL)
    if 'query_text' in instance:
      logging.info('📥 Request for Query')
      result = predictor.predict(mode='query', query_text=instance['query_text'])
    elif 'pdf_url' in instance:
      logging.info('📥 Request for PDF')
      result = predictor.predict(mode='document', pdf_url=instance['pdf_url'])
    else:
      raise ValueError("Invalid request format: specify 'query_text' or 'pdf_url'")

    # Return the result
    logging.info(f'✅ Prediction completed: {result}')
    return {'predictions': [result]}
  except HTTPException as e:
    logging.error(f'❌ HTTP error during prediction: {e}')
    raise
  except Exception as e:
    logging.error(f'❌ Error during prediction: {e}')
    raise HTTPException(status_code=500, detail=f'Internal error: {str(e)}')
