
from database.chroma import AsyncChromadbClient
from config import settings
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
import asyncio


router = APIRouter(prefix='/vectordb',tags=["orm"])


class InsertRequest(BaseModel):
    query: str
    metadatas: List[Dict[str, Any]]
    documents: List[str]
    ids: List[str]
    collection_name: str = "default"

class QueryRequest(BaseModel):
    query: str
    n_results: int = 10
    collection_name: str = "default"

chromadb_client = AsyncChromadbClient()


@router.post("/insert")
async def insert_data(request: InsertRequest):
    await chromadb_client.insert(
        query=request.query,
        metadatas=request.metadatas,
        documents=request.documents,
        ids=request.ids,
        collection_name=request.collection_name,
    )
    return {"message": "Data inserted successfully"}

@router.post("/query")
async def query_data(request: QueryRequest):
    results = await chromadb_client.query(
        query=request.query,
        n_results=request.n_results,
        collection_name=request.collection_name,
    )
    return results

@router.get("/collections")
async def list_collections():
    collections = await chromadb_client.list_collection()
    return {"collections": collections}

@router.delete("/collections/{collection_name}")
async def delete_collection(collection_name: str):
    await chromadb_client.delete_collection(collection_name)
    return {"message": f"Collection {collection_name} deleted successfully"}
