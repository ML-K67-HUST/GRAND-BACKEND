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

        self.redis_url = os.getenv("REDIS_URL")
        self.redis_port = os.getenv("REDIS_PORT")
        self.redis_password = os.getenv("REDIS_PASSWORD")

        self.google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.secret_key = os.getenv("SECRET_KEY")
        self.redirect_url = os.getenv("REDIRECT_URL")
        self.frontend_url = os.getenv("FRONTEND_URL")
        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
        self.JWT_REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY")

        self.security_on = False
settings = Settings()