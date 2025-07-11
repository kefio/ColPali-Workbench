# ColPali API

### Description
ColPali API helps manage and search documents by working with VERTEX and Vespa Cloud. It uses Google Cloud services: VERTEX for processing PDFs and Google Storage for storing them. Built with FastAPI, it connects various services and clients.

### Key Features

- **PDF Upload and Processing**: Upload PDFs to Google Cloud Storage and generate embeddings with Vertex AI.
- **Vespa Cloud Integration**: Manage Vespa Cloud applications for document indexing and searching.
- **Image and Text Handling**: Process images and text from PDFs for Vespa Cloud.
- **Search Functionality**: Perform advanced searches on indexed documents.

### Components

- **VespaClient** [`vespaClient.py`]: Handles Vespa Cloud interactions.
- **VertexClient** [`vertexClient.py`]: Creates embeddings with Vertex AI.
- **LlamaClient** [`llamaClient.py`]: Uses the LLaMA model via Together API.

### Getting Started

Follow the instructions in the readme.md file in the root of the Colpali-workbench repo.
