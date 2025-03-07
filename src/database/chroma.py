import chromadb
from config import settings
from chromadb.api import AsyncClientAPI, ClientAPI
import requests

class ChromadbClient:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ChromadbClient, cls).__new__(cls)
            cls._instance.client = chromadb.HttpClient(
                host=settings.chroma_endpoint,
            )
        return cls._instance

    def get_client(self) -> ClientAPI:
        return self.client


class AsyncChromadbClient:
    _instance = None
    _client = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AsyncChromadbClient, cls).__new__(cls)
        return cls._instance

    async def init(self):
        if not self._client:
            self._client = await chromadb.AsyncHttpClient(
                host=settings.chroma_endpoint,
            )
        return self

    async def get_client(self) -> AsyncClientAPI:
        if not self._client:
            await self.init()
        return self._client

    async def _get_embeddings(self,query=""):

        response = requests.post(
            f"{settings.embedding_client_url}/v1/embeddings",
            json={"input": query, "model": settings.chroma_model},
        )

        # Check if the response is successful
        if response.status_code == 200:
            print("Encode done!")
        else:
            print(
                "Error:  {response.status_code} , {response.text} "
            )
        return response.json()["data"][0]["embedding"]    
    
    async def insert(self, 
                    query, 
                    metadatas, 
                    documents, 
                    ids, 
                    collection_name="default"
        ):
        print(1111)
        client = await self.get_client()
        print(222)
        collection = await client.get_or_create_collection(name=collection_name)
        embeddings = await self._get_embeddings(query=query)
        await collection.add(
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
            ids=ids,
        )

    async def query(self, 
        query, 
        n_results=10, 
        collection_name="default"
    ):
        client = await self.get_client()
        collection = await client.get_collection(name=collection_name)
        embeddings = await self._get_embeddings(query)
        print('embeddings:\n',embeddings)
        results = await collection.query(query_embeddings=embeddings, n_results=n_results)
        return results

    async def list_collection(self):
        client = await self.get_client()
        collections = await client.list_collections()
        return [collection for collection in collections]

    async def delete_collection(self, collection_name):
        client = await self.get_client()
        await client.delete_collection(name=collection_name)