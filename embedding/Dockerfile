
FROM python:3.9

WORKDIR /app


COPY requirements.txt .


RUN pip install --no-cache-dir -r requirements.txt

RUN pip install -U ctranslate2 && \
    ct2-transformers-converter --model BAAI/bge-base-en-v1.5 --output_dir bge_model_ctranslate2 --force

COPY . .

EXPOSE 8002


CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
