from io import BytesIO
import torch
import numpy as np
import base64

from vespa.deployment import VespaCloud
from vespa.package import (
  RankProfile,
  Function,
  FirstPhaseRanking,
  SecondPhaseRanking,
  ApplicationPackage,
  Schema,
  Document,
  Field,
  FieldSet,
  HNSW,
)
from vespa.application import Vespa

from app.config import (
  VESPA_APP_PACKAGE_NAME,
  VESPA_ENDPOINT,
  VESPA_TENANT_NAME,
  VESPA_APP_NAME,
  VESPA_KEY_FILENAME,
  VESPA_CLOUD_SECRET_TOKEN,
)
from app.utils.logger import setup_logger

logger = setup_logger()


class VespaClient:
  """
  Client for interacting with Vespa Cloud.

  This class handles all operations with Vespa Cloud, including:
  - Initialization and configuration of the client
  - Creation and deployment of the application
  - Data feeding (feed)
  - Execution of queries

  The class supports both connecting to an existing app and creating
  a new Vespa Cloud application.
  """

  def __init__(self) -> Vespa:
    """
    Initializes the Vespa client using environment variables.

    """
    self.endpoint = VESPA_ENDPOINT
    self.app = None

    if self.endpoint:
      logger.info('Using an existing Vespa application...')
      self.app = Vespa(
        url=self.endpoint,
        vespa_cloud_secret_token=VESPA_CLOUD_SECRET_TOKEN,
      )
    else:
      logger.info('Creating a new Vespa application...')
      self.app = self._create_and_deploy_app()

  def _create_and_deploy_app(self) -> Vespa:
    """
    Creates and deploys a new Vespa Cloud application.
    I adapted from: https://pyvespa.readthedocs.io/en/latest/examples/pdf-retrieval-with-ColQwen2-vlm_Vespa-cloud.html

    This method:
    1. Creates the schema for PDF documents
    2. Configures fields for text, images, and embeddings
    3. Sets up the ranking profile using BM25 and MaxSim
    4. Configures HNSW for approximate nearest neighbor search
    5. Deploys the application on Vespa Cloud

    The schema includes:
    - An embedding field for binary vectors of images
    - Text fields for title and content with BM25
    - A raw field for base64-encoded images
    """

    logger.info('Creating a new schema for the Vespa app...')

    app_package = self.get_application_package(VESPA_APP_PACKAGE_NAME)

    deployment = VespaCloud(
      tenant=VESPA_TENANT_NAME,
      application=VESPA_APP_NAME,
      key_location=VESPA_KEY_FILENAME,
      application_package=app_package,
      application_root='app',
    )

    self.app = deployment.deploy()

    logger.info(f'Successfully deployed Vespa app: {self.app.url}')

    return self.app

  ### Utils
  def get_application_package(self, application_package_name: str) -> ApplicationPackage:
    """
    Get the application package for the Vespa app.

    Returns:
        ApplicationPackage: The application package
    """
    colpali_schema = Schema(
      name='pdf_page',
      document=Document(
        fields=[
          Field(name='id', type='string', indexing=['summary', 'index'], match=['word']),
          Field(name='url', type='string', indexing=['summary', 'index']),
          Field(
            name='title',
            type='string',
            indexing=['summary', 'index'],
            match=['text'],
            index='enable-bm25',
          ),
          Field(name='page_number', type='int', indexing=['summary', 'attribute']),
          Field(name='image', type='raw', indexing=['summary']),
          Field(
            name='text',
            type='string',
            indexing=['index'],
            match=['text'],
            index='enable-bm25',
          ),
          Field(
            name='embedding',
            type='tensor<int8>(patch{}, v[16])',
            indexing=[
              'attribute',
              'index',
            ],  # Adds HNSW index for candidate retrieval.
            ann=HNSW(
              distance_metric='hamming',
              max_links_per_node=32,
              neighbors_to_explore_at_insert=400,
            ),
          ),
        ]
      ),
      fieldsets=[FieldSet(name='default', fields=['title', 'text'])],
    )
    colpali_profile = RankProfile(
      name='default',
      inputs=[('query(qt)', 'tensor<float>(querytoken{}, v[128])')],
      functions=[
        Function(
          name='max_sim',
          expression="""
                        sum(
                            reduce(
                                sum(
                                    query(qt) * unpack_bits(attribute(embedding)) , v
                                ),
                                max, patch
                            ),
                            querytoken
                        )
                    """,
        ),
        Function(name='bm25_score', expression='bm25(title) + bm25(text)'),
      ],
      first_phase=FirstPhaseRanking(expression='bm25_score'),
      second_phase=SecondPhaseRanking(expression='max_sim', rerank_count=100),
    )
    colpali_schema.add_rank_profile(colpali_profile)

    app_package = ApplicationPackage(name=application_package_name, schema=[colpali_schema])

    return app_package

  ### Queries and data feeding methods ###
  async def feed_data(self, vespa_feed, schema='pdf_page'):
    """
    Uploads data to Vespa Cloud.

    Args:
        vespa_feed (list): List of documents to upload
        schema (str): Name of the schema to use

    Each document must contain:
    - id: Unique identifier
    - embedding: Binary feature vectors
    - text: Document text
    - image: Image in base64 format
    """
    if not self.app:
      raise RuntimeError('Vespa app not initialized.')

    logger.info(f'Starting to feed data to Vespa schema: {schema}')
    logger.info(f'Number of documents to feed: {len(vespa_feed)}')

    async with self.app.asyncio(connections=1, timeout=180) as session:
      for page in vespa_feed:
        try:
          # Verifica e sanitizza i dati prima dell'invio
          clean_page = {
            'id': str(page['id']),
            'url': str(page.get('url', '')),
            'title': str(page.get('title', '')),
            'page_number': int(page.get('page_number', 0)),
            'image': str(page.get('image', '')),
            'text': str(page.get('text', '')),
            'embedding': page.get('embedding', []),
          }

          logger.info(f"Feeding document ID: {clean_page['id']}")
          response = await session.feed_data_point(schema=schema, data_id=clean_page['id'], fields=clean_page)
          if response.is_successful():
            logger.info(f"Successfully fed document ID: {page['id']}")
          else:
            logger.error(f"Error in feed for document ID: {page['id']}, Response: {response.json()}")
        except Exception as e:
          logger.error(f"Exception occurred while feeding document ID: {page['id']}, Error: {str(e)}")

    logger.info('Completed feeding data to Vespa')

  async def query(self, query_text, query_embeddings, hits=3, ranking='default'):
    """
    Executes a query on Vespa Cloud.

    Supports two ranking modes:
    1. "default": Uses BM25 + MaxSim for ranking
    2. "retrieval-and-rerank": Uses nearestNeighbor with Hamming distance

    Args:
        query_text (str): Text of the query
        query_embeddings (tensor): Embedding of the query from the ColQwen2 model
        hits (int): Number of results to return
        ranking (str): Ranking strategy to use

    Returns:
        VespaQueryResponse: Query results with scoring
    """
    if not self.app:
      raise RuntimeError('Vespa app not initialized.')

    logger.info(f'Executing query: {query_text}')
    # logger.info(f"Query embeddings: {query_embeddings}")

    async with self.app.asyncio(connections=1, timeout=120) as session:
      if ranking == 'default':
        # Use ranking based on BM25 + MaxSim
        float_query_embedding = {k: v.tolist() for k, v in enumerate(query_embeddings)}
        # logger.info(f"Float query embedding: {float_query_embedding}")
        response = await session.query(
          yql='select title,url,image,page_number from pdf_page where userInput(@userQuery)',
          ranking=ranking,
          userQuery=query_text,
          timeout=120,
          hits=hits,
          body={'input.query(qt)': float_query_embedding, 'presentation.timing': True},
        )
      else:
        # Use ranking based on nearestNeighbor (Work in progress!)
        target_hits_per_query_tensor = 20
        float_query_embedding = {k: v.tolist() for k, v in enumerate(query_embeddings)}
        binary_query_embeddings = dict()
        for k, v in float_query_embedding.items():
          binary_query_embeddings[k] = np.packbits(np.where(np.array(v) > 0, 1, 0)).astype(np.int8).tolist()

        query_tensors = {
          'input.query(qtb)': binary_query_embeddings,
          'input.query(qt)': float_query_embedding,
        }

        # Add tensors for nearestNeighbor
        for i in range(len(binary_query_embeddings)):
          query_tensors[f'input.query(rq{i})'] = binary_query_embeddings[i]

        # Construct the nearestNeighbor query
        nn = [
          f'({{targetHits:{target_hits_per_query_tensor}}}nearestNeighbor(embedding,rq{i}))'
          for i in range(len(binary_query_embeddings))
        ]
        nn = ' OR '.join(nn)

        response = await session.query(
          yql=f'select title,url,image,page_number from pdf_page where {nn}',
          ranking='retrieval-and-rerank',
          timeout=120,
          hits=hits,
          body={**query_tensors, 'presentation.timing': True},
        )
      logger.info(f'Query response status code: {response.status_code}')
      # logger.info(f"Query response content: {response.content}")

      if response.status_code != 200:
        logger.error(f'Query failed with status code: {response.status_code}')
        raise RuntimeError(f'Query failed with status code: {response.status_code}')

      return response

  def build_vespa_feed(self, pdfs_data):
    """
    Prepares data for insertion into Vespa.

    Key functionalities:
    1. Converts embeddings into binary format
    2. Resizes and encodes images in base64
    3. Organizes metadata into Vespa-compatible format

    Args:
        pdfs_data (list): A list of dictionaries containing PDF data.

    Returns:
        list: A list of documents formatted for Vespa.
    """

    def process_embedding(patch_embedding):
      """
      Converts an embedding into compressed binary format.

      Args:
          patch_embedding: Embedding to process

      Returns:
          str: Hexadecimal string of the binary embedding
      """
      # Convert the tensor to numpy and ensure it's a float
      patch_array = patch_embedding.numpy()
      # Perform binarization
      binary = np.where(patch_array > 0, 1, 0)
      # Convert to bit-packed format
      return np.packbits(binary).astype(np.int8).tobytes().hex()

    def get_base64_image(image):
      """
      Converts an image to base64 format.

      Args:
          image: A PIL Image or base64 string

      Returns:
          str: Base64-encoded string of the image
      """
      if isinstance(image, str):
        return image
      buffered = BytesIO()
      image.save(buffered, format='JPEG')
      return str(base64.b64encode(buffered.getvalue()), 'utf-8')

    def resize_image(image, max_height=800):
      """
      Resizes an image while maintaining aspect ratio.

      Args:
          image: Image to resize
          max_height (int): Desired maximum height

      Returns:
          Image: Resized image
      """
      if isinstance(image, str):
        return image
      if not hasattr(image, 'size'):
        return image
      width, height = image.size
      if height > max_height:
        ratio = max_height / height
        return image.resize((int(width * ratio), max_height))
      return image

    vespa_feed = []
    for pdf in pdfs_data:
      url = pdf['url']
      title = pdf['title']
      for page_number, (page_text, embedding_list, image) in enumerate(
        zip(pdf['texts'], pdf['embeddings'], pdf['images'])
      ):
        # Step 1: Deserializzare l'embedding da lista a tensore
        embedding_tensor = torch.tensor(embedding_list, dtype=torch.float32)

        # Step 2: Convertire ogni embedding in formato binario
        embedding_dict = {}
        for idx, patch_embedding in enumerate(embedding_tensor):
          binary_vector = process_embedding(patch_embedding)
          embedding_dict[idx] = binary_vector

        # Step 3: Convertire l'immagine in base64
        base_64_image = get_base64_image(resize_image(image, 640))

        # Step 4: Creare il documento per Vespa
        page = {
          'id': str(hash(url + str(page_number))),  # Convert the hash to a string
          'url': url,
          'title': title,
          'page_number': page_number,
          'image': base_64_image,
          'text': page_text,
          'embedding': embedding_dict,
        }
        vespa_feed.append(page)

    return vespa_feed
