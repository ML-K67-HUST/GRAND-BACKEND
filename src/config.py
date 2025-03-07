import os
from dotenv import load_dotenv

load_dotenv(override=True)

                
class Settings:
    def __init__(self):
        self.together_api_key = os.getenv("TOGETHER_AI_API_KEY")
        self.mongodb_url = os.getenv("MONGODB_URL")
        self.mongodb_timenest_db_name = os.getenv("MONGDB_TIMENEST_DN_NAME")

        self.chroma_endpoint = os.getenv("chroma_client_url")
        self.embedding_client_url = os.getenv("embedding_client_url")
        self.chroma_model = os.getenv("chroma_model")

        self.postgres_client_url = os.getenv("AWS_POSTGRES_URL")
        self.postgres_password = os.getenv("POSTGRES_PASSWORD")
        self.postgres_user = os.getenv("POSTGRES_USER")
        self.postgres_port = os.getenv("POSTGRES_PORT")

settings = Settings()