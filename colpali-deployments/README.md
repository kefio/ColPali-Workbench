# Deploying the Colpali Model on Google Vertex AI

This guide provides a streamlined process for deploying the Colpali model on **Google Vertex AI**. Follow these steps to build, upload, create an endpoint, and deploy your model efficiently.

## Prerequisites

Ensure you have the following before proceeding:

- **Google Cloud SDK** installed and configured.
- **Docker** installed for building container images.
- Appropriate **Google Cloud IAM permissions** for AI Platform operations.
- **Cloud Build API** enabled in your Google Cloud project.

## Deployment Steps

### Step 1: Build the Container Image
**Estimated Time:** ~15-20 minutes

Use Cloud Build to create the container image:

```bash
gcloud builds submit --config=cloudbuild.yaml .
```

### Step 2: Upload the Model
**Estimated Time:** ~5-10 minutes

Upload the Colpali model to Vertex AI with the following command. Replace placeholders with your specific values:

```bash
gcloud ai models upload \
  --region=${PREFERRED_REGION} \
  --display-name=${MODEL_NAME} \
  --container-image-uri=gcr.io/${PROJECT_ID}/colpali-model:latest \
  --container-predict-route=/predict \
  --container-health-route=/health
```

- **${PREFERRED_REGION}:** The desired region for deployment.
- **${MODEL_NAME}:** Your model’s display name.
- **${PROJECT_ID}:** Your Google Cloud project ID.

You can verify available endpoints with the following command:

```bash
gcloud ai endpoints list
```

> **Note:** Steps 3 and 4 can be performed via the Google Cloud Console for better handling of potential timeout issues.

### Step 3: Create an Endpoint
**Estimated Time:** ~5 minutes

Create an endpoint for deploying the model:

```bash
gcloud ai endpoints create \
  --region=${PREFERRED_REGION} \
  --display-name=${ENDPOINT_NAME}
```

- **${PREFERRED_REGION}:** The region where the endpoint will be created.
- **${ENDPOINT_NAME}:** Your desired endpoint name.

### Step 4: Deploy the Model to the Endpoint
**Estimated Time:** ~25-30 minutes

Deploy the model to the created endpoint. Replace the placeholders with your actual values:

```bash
gcloud ai endpoints deploy-model [VERTEX_ENDPOINT_ID] \
  --region=${PREFERRED_REGION} \
  --model=${MODEL_ID} \
  --display-name=${DEPLOYMENT_NAME} \
  --machine-type=n1-standard-8 \
  --accelerator=count=1,type=nvidia-tesla-t4 \
  --traffic-split=0=100
```

- **${PREFERRED_REGION}:** The deployment region.
- **${MODEL_ID}:** The model ID obtained during the upload step.
- **${DEPLOYMENT_NAME}:** Your deployment’s display name.

To list available endpoints and models, use the following commands respectively:

```bash
gcloud ai endpoints list
gcloud ai models list
```

---

With these steps, your Colpali model should now be successfully deployed on Google Vertex AI. For further details, refer to the [Google Vertex AI documentation](https://cloud.google.com/vertex-ai/docs).