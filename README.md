# Colpali Workbench

## Overview

**Colpali Workbench** is an integrated system designed to facilitate efficient document indexing, querying, and management using **ColPali** (Faysse et al., 2024), a groundbreaking Vision Language Model specifically designed for document retrieval. 

### About ColPali

ColPali represents a paradigm shift in document retrieval by leveraging **Vision Language Models (VLMs)** to construct multi-vector embeddings directly from document images, eliminating the need for complex OCR and layout recognition pipelines. Based on the research paper ["ColPali: Efficient Document Retrieval with Vision Language Models"](https://arxiv.org/abs/2407.01449) (accepted at **ICLR 2025**), this approach treats document pages as images and processes them through a **PaliGemma-3B** backbone with **ColBERT-style late interaction mechanisms**.

**Key innovations:**
- **Visual-first approach**: Processes document page images directly, capturing both textual content and visual elements (tables, charts, layout, fonts)
- **Multi-vector embeddings**: Generates 1024 patch embeddings (128-dimensional each) per page using Vision Transformer architecture
- **Late interaction**: Employs ColBERT methodology for efficient query-document matching through MaxSim operations
- **State-of-the-art performance**: Outperforms traditional text-based retrieval systems on the **ViDoRe benchmark** by significant margins

**Research background**: Developed through collaboration between *CentraleSupélec*, *Illuin Technology*, *Equall.ai*, and *ETH Zürich*, ColPali addresses the inherent limitations of traditional RAG systems that struggle with visually rich documents. The model was trained on 127,460 query-page pairs and demonstrates superior performance across multiple domains and languages.

This workbench implements the complete ColPali pipeline, providing a production-ready solution for organizations seeking to leverage cutting-edge document retrieval technology.

## Table of Contents

- [Architecture](#architecture)
  - [Core Components](#core-components)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Running the System](#running-the-system)
- [Usage Phases](#usage-phases)
  - [Vespa Deploy](#vespa-deploy)
  - [Document Indexing](#document-indexing)
  - [Query Retrieval and Response](#query-retrieval-and-response)
- [Setting Up Environment Variables](#setting-up-environment-variables)

## Architecture



<img width="1058" alt="Components" src="https://github.com/user-attachments/assets/62c7fb80-985f-40f2-9715-961324f5c99b" />

Colpali Workbench consists of the following main components:

### Core Components

1. **Colpali-UI (React):**  
   The user interface built with **React** enables interaction with the system. It allows users to upload documents, perform searches, and retrieve results through an intuitive web-based platform.

2. **Colpali-API (FastAPI Backend Orchestrator):**  
   The **FastAPI** backend acts as the central orchestrator, managing communication between all other components. Its responsibilities include:
   - Coordinating document uploads, storage (**Google Storage**), and embedding generation (**VERTEX**).
   - Feeding data into **VESPA Cloud** for indexing.
   - Processing user queries and retrieving results (2 types of ranking implemented: *"BM25 + MaxSim"* and *"nearestNeighbor + Hamming distance"*).
   - Generating natural language responses through the **LLAMA Client**.

3. **Vertex AI (Colpali-Deployments):**  
   A **FastAPI Docker container** deployed on **Google Vertex AI** that handles embedding generation. It processes both documents and queries, returning embeddings to the backend for indexing or retrieval.

4. **Google Cloud Storage (G-BUCKET):**  
   The cloud storage solution where uploaded documents are securely stored. Documents are referenced via public URLs, which are passed to the **Colpali-Deployments** for embedding generation.

5. **Vespa Cloud:**  
   The multi-vector database used to store embeddings and rank documents with "Late Interaction."

6. **LLAMA 3.2 VLM (Together AI):**  
   The Visual Language Model integrated via the backend to generate intelligent natural language responses based on the retrieved documents and query context.

---

This architecture overview provides a detailed understanding of how the components interact. For specific details on each component, refer to their individual README files.

## Getting Started

### Prerequisites

Before setting up Colpali Workbench, ensure you have the following installed:

- **Colpali Deployment on VERTEX**: Please refer to the `/colpali-deployments` README file.
- **Google Cloud Account**: Access to Google Cloud services like Vertex AI and Cloud Storage.
- **Vespa Cloud Account**: Create an account here: https://vespa.ai/developer/

### Installation

Follow these steps to set up the Colpali Workbench system:

1. **Set Up Environment Variables**

    Each component may require specific environment variables. Please define the necessary variables in the `docker-compose.yml`.

    ```
    VERTEX_ENDPOINT_ID=your-colpali-vertex-endpoint-id-number
    VERTEX_PROJECT_ID=your-vertex-project-name
    VERTEX_LOCATION=your-location (ex: us-central1)
    VESPA_TENANT_NAME=your-tenant-name
    VESPA_APP_NAME=your-app-name
    TOGETHER_API_KEY=your-together-api-key
    HUGGINGFACE_TOKEN=hf_your_huggingface_token_here
    ```

    You can leave the following environment variables with these values:
    ```
    PDF_GBUCKET_NAME=colpali_pdf
    GOOGLE_APPLICATION_CREDENTIALS=gcloud/gapp_credentials.json
    VESPA_KEY_FILENAME=keys/colpali.pem
    CACHE_DIR_ROOT_PATH=response_cache
    CACHE_DOC_RESPONSE_FILE_NAME=doc_last_response.json
    CACHE_QUERY_RESPONSE_FILE_NAME=query_last_response.json
    ```

2. **Security Best Practices for Tokens**

    ⚠️ **IMPORTANTE - Gestione Sicura dei Token:**
    
    - **MAI inserire token/segreti direttamente nel codice sorgente**
    - **USA sempre variabili d'ambiente** per gestire token sensibili
    - **Aggiungi `.env` al `.gitignore`** per evitare commit accidentali
    - **Per produzione, usa servizi di gestione segreti** come Google Secret Manager
    
    **Esempio di gestione sicura per il token Hugging Face:**
    ```bash
    # Crea un file .env nella directory del progetto (NON committare questo file!)
    echo "HUGGINGFACE_TOKEN=hf_your_actual_token_here" > .env
    
    # Avvia Docker con le variabili d'ambiente
    docker run -e HUGGINGFACE_TOKEN=$HUGGINGFACE_TOKEN your_image
    ```

3. **Build and Deploy Components**

    Use Docker Compose to build and run all components simultaneously.

    ```bash
    docker compose up --build
    ```

### Running the System

After successfully building and deploying the containers, open your web browser and navigate to `http://localhost:3000` to access the frontend interface.

## Usage Phases

The system operates across two main phases: **Document Indexing** and **Query Retrieval and Response**.

### Vespa Deploy

You need to deploy the Vespa application before document indexing or query retrieval. This ensures you have the correct multi-vector setup to run the application. 

How to do: Click the **Deploy App on Vespa** button on the top-right corner and wait until the green light appears. It could take 1-2 minutes.

### Document Indexing

<img width="892" alt="Doc Indexing" src="https://github.com/user-attachments/assets/2b4beec0-b223-46ea-9c1e-cfcd85fdb707" />

This phase prepares documents for efficient querying:
- **User Upload:** Documents are uploaded through **Colpali-UI** and sent to the **Colpali-API** backend.
- **Storage in G-BUCKET:** Documents are stored in **Google Cloud Storage**, and their public URLs are generated.
- **Embedding Generation:** The backend sends the document URLs to **Colpali-Deployments**, deployed on **Vertex AI**, for embedding generation.
- **Index Feeding:** The embeddings and metadata are processed by the **VESPA Feed Builder** and fed into **VESPA Cloud** for indexing.

### Query Retrieval and Response

<img width="836" alt="Retrieval" src="https://github.com/user-attachments/assets/d71984a2-3cc7-43d4-9d79-9c558f556242" />

This phase retrieves and processes user queries:
- **User Query:** Queries are submitted through **Colpali-UI** and sent to the backend.
- **Embedding Generation:** The **Colpali-Deployments** container generates embeddings for the query text.
- **VESPA Querying:** The embeddings are sent to **VESPA Cloud**, which retrieves:
  - **Top K documents** using HSNW,
  - Refined results through **Late Interaction**.
- **Response Generation:** The backend processes the retrieved documents using **LLAMA 3.2**, generating a natural language response.
- **Response Delivery:** The generated response is sent back to the user through **Colpali-UI**.

## Setting Up Environment Variables

1. **GOOGLE_APPLICATION_CREDENTIALS**: This is the path to your Google Cloud credentials JSON file.
    - **How to obtain**:
        - Go to the [Google Cloud Console](https://console.cloud.google.com/).
        - Navigate to **IAM & Admin** > **Service Accounts**.
        - Create a new service account or select an existing one.
        - Add the following roles: `Storage Admin`, `Vertex AI Administrator`, `Vertex AI Viewer`.
        - Generate a new key in JSON format and save it to your project directory (e.g., `colpali-api/gapp_credentials.json`).

2. **ENDPOINT_ID**, **VERTEX_PROJECT_ID**, **VERTEX_LOCATION**: Identifiers for your Vertex AI deployment.
    - **How to obtain**:
        - Navigate to [Vertex AI](https://console.cloud.google.com/vertex-ai) in the Google Cloud Console.
        - Deploy your ColPali model and note the **Endpoint ID**, **Project ID**, and **Location** from the deployment details (please refer to the colpali-deployments README file).

3. **VESPA_TENANT_NAME**, **VESPA_APP_NAME**, **VESPA_KEY_FILENAME**: Configuration details for your Vespa Cloud tenant and application.
    - **How to obtain**:
        - Sign up and log in to [Vespa Cloud](https://cloud.vespa.ai/).
        - Create a tenant and note the tenant name from your Vespa Cloud dashboard.
        - Choose an app name as you wish.
        - Go to Vespa Dashboard > Account > Keys and create a new key.
        - Download the .pem file, rename it `colpali.pem`, and copy it into the */colpali-api/app/vespa/keys* folder.

4. **TOGETHER_API_KEY**: API key for accessing the LLaMA 3.2 model via Together API.
    - **How to obtain**:
        - Register for an account on [Together AI](https://together.com/) and generate an API key from your account dashboard.

5. **HUGGINGFACE_TOKEN**: Token per accedere ai modelli Hugging Face (richiesto per ColPali).
    - **Come ottenerlo**:
        - Registrati su [Hugging Face](https://huggingface.co/) e vai alle [impostazioni del token](https://huggingface.co/settings/tokens)
        - Crea un nuovo token con permessi di lettura
        - **⚠️ IMPORTANTE**: Non inserire mai questo token direttamente nel Dockerfile o nel codice sorgente
        - Usa sempre variabili d'ambiente: `export HUGGINGFACE_TOKEN=hf_your_token_here`

6. **CACHE_DIR_ROOT_PATH**, **CACHE_DOC_RESPONSE_FILE_NAME**, **CACHE_QUERY_RESPONSE_FILE_NAME**: Configuration for caching responses.
    - **How to set**:
        - Specify the desired directory path and file names for caching responses as per your preference. You can leave the default values.


## Future Improvements
- **✅ Security Issue in Dockerfile - RISOLTO**  
  Il problema del token Hugging Face hardcoded nel `Dockerfile` in **colpali-deployments/vertex-deployment/** è stato risolto. Ora i token devono essere passati come variabili d'ambiente seguendo le best practices di sicurezza documentate nella sezione di installazione.

- **Image Resizing and Compression**  
  Optimize image resizing and compression during embedding creation and front-back communication to enhance performance and reduce resource usage.

- **Handling Large PDF Files**  
  Implement automatic splitting of large PDF files to prevent timeouts. Currently, files larger than 1.5MB (e.g., 52 pages, 3MB) cause issues as the response JSON becomes too large (13MB) due to embedded images.

- **Multiple File Uploads**  
  Enable the system to support uploading multiple files simultaneously instead of restricting to one file at a time.

- **Vespa Authentication via Certificate File**  
  Fix the authentication process to Vespa using certificate files to ensure secure and reliable connections.

## Citations and References

This project builds upon the groundbreaking research presented in the ColPali paper. Please cite the original work when using this system:

### Primary Citation

```bibtex
@misc{faysse2024colpaliefficientdocumentretrieval,
    title={ColPali: Efficient Document Retrieval with Vision Language Models}, 
    author={Manuel Faysse and Hugues Sibille and Tony Wu and Bilel Omrani and Gautier Viaud and Céline Hudelot and Pierre Colombo},
    year={2024},
    eprint={2407.01449},
    archivePrefix={arXiv},
    primaryClass={cs.IR},
    url={https://arxiv.org/abs/2407.01449},
    note={Accepted at ICLR 2025}
}
```

### Key References

- **ColPali Paper**: [arXiv:2407.01449](https://arxiv.org/abs/2407.01449)
- **ColPali Models**: [Hugging Face - vidore/colpali](https://huggingface.co/vidore/colpali)
- **ViDoRe Benchmark**: [Hugging Face Leaderboard](https://huggingface.co/spaces/vidore/vidore-leaderboard)
- **PaliGemma Model**: [google/paligemma-3b-mix-448](https://huggingface.co/google/paligemma-3b-mix-448)
- **ColBERT Architecture**: [Neural Information Retrieval](https://github.com/stanford-futuredata/ColBERT)

### Related Work

- Khattab, O., & Zaharia, M. (2020). ColBERT: Efficient and effective passage search via contextualized late interaction over BERT. *SIGIR*.
- Bevilacqua, M., et al. (2024). PaliGemma: A versatile 3B VLM for transfer. *arXiv preprint*.

### Acknowledgments

Special thanks to the research teams at CentraleSupélec, Illuin Technology, Equall.ai, and ETH Zürich for their pioneering work on vision-based document retrieval.

---

*This README was generated to provide a comprehensive overview of the Colpali Workbench system, its components, and guidelines for setup and contribution. For detailed instructions on each component, please refer to their respective README files.*

