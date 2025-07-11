import torch
from pdf2image import convert_from_bytes
from pypdf import PdfReader
from io import BytesIO
import base64
from colpali_engine.models import ColQwen2, ColQwen2Processor
import requests
from typing import Dict, Any, List, Union, Literal, Optional
from enum import Enum
from pydantic import BaseModel
import os
import time
import logging

os.environ['TOKENIZERS_PARALLELISM'] = 'false'


# Define input types
class PredictionMode(str, Enum):
  DOCUMENT = 'document'
  QUERY = 'query'


class PredictionInput(BaseModel):
  mode: PredictionMode
  pdf_url: Optional[str] = None
  query_text: Optional[str] = None


class Predictor:
  # Initialize the ColQwen2 model and processor, called at application startup
  def setup(self):
    try:
      logging.info('🚀 Initializing the model...')
      self.model_name = 'vidore/colqwen2-v0.1'
      logging.info(f'📦 Loading model from: {self.model_name}')

      # Determine the device. If a GPU is available, use it, otherwise CPU.
      device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
      logging.info(f'💻 Using device: {device}')

      self.model = ColQwen2.from_pretrained(
        self.model_name,
        torch_dtype=torch.bfloat16,
        device_map='auto',
      ).eval()

      logging.info('🔧 Loading processor...')
      self.processor = ColQwen2Processor.from_pretrained(self.model_name)

      logging.info('✅ Setup completed successfully!')
    except Exception as e:
      logging.error(f'❌ Error during model setup: {e}')
      raise

  def setup_01(self):
    try:
      logging.info('🚀 Initializing the model...')
      self.model_name = 'vidore/colqwen2-v0.1'
      logging.info(f'📦 Loading model from: {self.model_name}')
      self.model = ColQwen2.from_pretrained(
        self.model_name,
        torch_dtype=torch.bfloat16,
        device_map='auto',
      )
      logging.info('🔧 Loading processor...')
      self.processor = ColQwen2Processor.from_pretrained(self.model_name)
      self.model = self.model.eval()
      logging.info('✅ Setup completed successfully!')
    except Exception as e:
      logging.error(f'❌ Error during model setup: {e}')
      raise

  # Download the PDF from the provided URL
  # Input: url (str)
  # Output: BytesIO (PDF content)
  def download_pdf(self, url):
    try:
      logging.info(f'📥 Downloading PDF from: {url}')
      response = requests.get(url, timeout=10)  # 10 seconds timeout
      if response.status_code == 200:
        logging.info('✅ Download completed successfully!')
        return BytesIO(response.content)
      else:
        error_msg = f'❌ Download failed with status code: {response.status_code}'
        logging.error(error_msg)
        raise Exception(error_msg)
    except requests.exceptions.Timeout:
      error_msg = '❌ Download failed: timeout'
      logging.error(error_msg)
      raise Exception(error_msg)
    except Exception as e:
      logging.error(f'❌ Error during PDF download: {e}')
      raise

  # Extract content (text and images) from the PDF
  # Input: pdf_file (BytesIO)
  # Output: tuple (images, page_texts)
  def get_pdf_content(self, pdf_file):
    try:
      logging.info('🔍 Starting PDF content extraction...')

      # Read the entire PDF into memory once
      pdf_data = pdf_file.getvalue()

      temp_file = '/tmp/temp.pdf'
      logging.info('💾 Saving temporary PDF...')
      with open(temp_file, 'wb') as f:
        f.write(pdf_data)

      logging.info('📄 Extracting text...')
      reader = PdfReader(temp_file)
      page_texts = []
      for page_number in range(len(reader.pages)):
        logging.info(f'  📃 Processing page {page_number + 1}/{len(reader.pages)}')
        page = reader.pages[page_number]
        text = page.extract_text()
        page_texts.append(text)

      logging.info('🖼️ Extracting images...')
      # Now using pdf_data directly for convert_from_bytes,
      # avoiding re-reading from pdf_file which might have been consumed already.
      images = convert_from_bytes(pdf_data)
      logging.info(f'📊 Extracted {len(images)} images and {len(page_texts)} texts')
      return images, page_texts
    except Exception as e:
      logging.error(f'❌ Error during PDF content extraction: {e}')
      raise

  def get_pdf_content_old(self, pdf_file):
    try:
      logging.info('🔍 Starting PDF content extraction...')
      temp_file = 'temp.pdf'
      logging.info('💾 Saving temporary PDF...')
      with open(temp_file, 'wb') as f:
        f.write(pdf_file.read())
      logging.info('📄 Extracting text...')
      reader = PdfReader(temp_file)
      page_texts = []
      for page_number in range(len(reader.pages)):
        logging.info(f'  📃 Processing page {page_number + 1}/{len(reader.pages)}')
        page = reader.pages[page_number]
        text = page.extract_text()
        page_texts.append(text)
      logging.info('🖼️ Extracting images...')
      images = convert_from_bytes(pdf_file.getvalue())
      logging.info(f'📊 Extracted {len(images)} images and {len(page_texts)} texts')
      return images, page_texts
    except Exception as e:
      logging.error(f'❌ Error during PDF content extraction: {e}')
      raise

  # Convert the image to base64 format
  # Input: image (PIL.Image)
  # Output: str (image in base64)
  def get_base64_image(self, image):
    try:
      logging.info('🔄 Converting image to base64...')
      buffered = BytesIO()
      image.save(buffered, format='JPEG')
      return str(base64.b64encode(buffered.getvalue()), 'utf-8')
    except Exception as e:
      logging.error(f'❌ Error during image to base64 conversion: {e}')
      raise

  # Perform prediction based on query or document
  # Input: mode (str), pdf_url (str), query_text (str)
  # Output: Union[List[Dict[str, Any]], Dict[str, Any]] (prediction result)
  def predict(
    self,
    mode: Literal['document', 'query'],
    pdf_url: str = None,
    query_text: str = None,
  ) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    try:
      logging.info('\n🎯 Starting prediction...')
      start_time = time.time()
      # Log device info
      is_cuda_available = torch.cuda.is_available()
      logging.info(f'💻 torch.cuda.is_available(): {is_cuda_available}')
      if self.model is not None:
        # Try to extract the device of the first parameter of the model
        first_param = next(self.model.parameters(), None)
        if first_param is not None:
          logging.info(f'💻 Model parameters device: {first_param.device}')
        else:
          logging.info('💻 No parameters found in model to infer device.')
      else:
        logging.info('💻 Model is not initialized.')

      # Check input conditions
      if mode == 'document':
        if pdf_url is None:
          raise ValueError('PDF URL is required in document mode')
        logging.info(f'🔗 PDF URL: {pdf_url}')

        # Download and process the PDF
        pdf_file = self.download_pdf(pdf_url)
        logging.info('📄 PDF downloaded successfully')
        images, texts = self.get_pdf_content(pdf_file)
        logging.info(f'📄 Extracted {len(images)} images and {len(texts)} texts from PDF')

        # Resize the image while maintaining the aspect ratio
        # Input: image (PIL.Image), max_height (int)
        # Output: PIL.Image (resized)
        def resize_image(image, max_height=512):
          width, height = image.size
          if height > max_height:
            ratio = max_height / height
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            logging.info(f'🔄 Resizing image from {width}x{height} to {new_width}x{new_height}')
            return image.resize((new_width, new_height))
          return image

        batch_size = 2  # or a smaller value to fit within memory limits
        page_embeddings = []
        for i in range(0, len(images), batch_size):
          sub_batch = images[i : i + batch_size]
          logging.info(f'🔄 Processing image batch {i//batch_size + 1}/{(len(images) + batch_size - 1) // batch_size}')

          # Resize images before processing
          sub_batch_resized = [resize_image(img, max_height=300) for img in sub_batch]
          logging.info(f'🔄 Resized {len(sub_batch_resized)} images')

          batch_inputs = self.processor.process_images(sub_batch_resized).to(self.model.device)
          with torch.no_grad():
            batch_embeddings = self.model(**batch_inputs)
            page_embeddings.extend(list(torch.unbind(batch_embeddings.to('cpu'))))  # nuova versione (testing)
            logging.info(f'🧠 Generated embeddings for batch {i//batch_size + 1}')

        page_embeddings = [e.tolist() for e in page_embeddings]  # nuova versione (testing)

        logging.info(f'🔗 Concatenated all batch embeddings, total elements: {len(page_embeddings)}')

        # cooking the final result
        pdf_data = {
          'url': pdf_url,
          'title': pdf_url.split('/')[-1],
          'images': [self.get_base64_image(img) for img in images],
          'texts': texts,
          'embeddings': page_embeddings,  # .tolist(),
        }

        logging.info('✨ Document prediction completed successfully!')
        logging.info(f'⏱️ Total time: {time.time() - start_time} seconds')
        return [pdf_data]

      elif mode == 'query':
        if query_text is None:
          raise ValueError('Query is required in query mode')
        logging.info(f'📝 Query text: {query_text}')
        logging.info('🧠 Generating query embeddings...')

        # Process the query
        batch_query = self.processor.process_queries([query_text])
        batch_query = {k: v.to(self.model.device) for k, v in batch_query.items()}
        logging.info(f'📥 Query inputs moved to device: {self.model.device}')

        with torch.no_grad():
          # Get query embeddings
          embeddings_query = self.model(**batch_query)
          logging.info('🧠 Generated query embeddings')

        # Move embeddings to CPU and convert to list
        embeddings_query_cpu = embeddings_query.cpu().tolist()
        logging.info('📤 Query embeddings moved to CPU')

        result = {
          'query': query_text,
          'embeddings': embeddings_query_cpu,
        }

        logging.info('✨ Query prediction completed successfully!')
        logging.info(f'⏱️ Total time: {time.time() - start_time} seconds')
        return result

    except Exception as e:
      logging.error(f'❌ Error during prediction: {e}')
      raise
