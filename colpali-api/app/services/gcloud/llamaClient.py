import os
from google.cloud import aiplatform
from PIL import Image
from together import Together

import logging  # Added to fix NameError

logger = logging.getLogger(__name__)

aiplatform.init(
  project=os.environ['VERTEX_PROJECT_ID'],
  location=os.environ['VERTEX_LOCATION'],
)


async def generate_response_from_llama(image: Image, query_text: str):
  """
  Generate a response from the LLaMA model using Together API.

  Args:
      image (Image): PIL Image object to send to the model.
      query_text (str): Query text to send to the model.

  Returns:
      str: Response from the model.
  """
  client = Together(api_key=os.environ['TOGETHER_API_KEY'])

  # Create a chat completion request
  response = client.chat.completions.create(
    model='meta-llama/Llama-3.2-90B-Vision-Instruct-Turbo',
    messages=[
      {
        'role': 'user',
        'content': [
          {'type': 'text', 'text': f'{query_text} Cite the text you used as a reference for the answer.'},
          {
            'type': 'image_url',
            'image_url': {
              'url': f'data:image/jpeg;base64,{image}',  # retrieved page image
            },
          },
        ],
      }
    ],
    max_tokens=300,
  )

  return response.choices[0].message.content
