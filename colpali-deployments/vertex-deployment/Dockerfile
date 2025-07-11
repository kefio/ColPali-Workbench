

###### SIMPLIFIED VERSION BY ALE FOR DEV #########

FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime

RUN apt-get update && apt-get install -y \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app

ENV POETRY_VERSION=1.6.1
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /root/.local/bin/poetry /usr/local/bin/poetry

RUN poetry config virtualenvs.create false

RUN mkdir -p /root/.cache/huggingface/hub
ENV HF_HOME="/root/.cache/huggingface"

# Hugging Face token will be passed as environment variable at runtime
# Use: docker run -e HUGGINGFACE_TOKEN=your_token_here ... 
ENV TOKENIZERS_PARALLELISM=false

COPY pyproject.toml poetry.lock* ./

RUN poetry config installer.max-retries 5 && \
    poetry install --no-interaction --no-ansi || \
    (sleep 5 && poetry install --no-interaction --no-ansi)

# Increase timeout and increase retries 
ENV POETRY_HTTP_TIMEOUT=600
ENV POETRY_HTTP_RETRIES=5


COPY . .

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--timeout-keep-alive", "300"]



