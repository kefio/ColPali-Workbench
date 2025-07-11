FROM python:3.10-slim
WORKDIR /app
RUN pip install poetry
RUN poetry config repositories.pytorch-cpu https://download.pytorch.org/whl/cpu
RUN poetry config virtualenvs.create false
COPY pyproject.toml poetry.lock /app/
ENV POETRY_HTTP_TIMEOUT=600
RUN poetry install --only main --no-interaction --no-ansi
RUN pip install vespacli
COPY . /app
RUN chmod -R 755 /app
EXPOSE 8000
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]