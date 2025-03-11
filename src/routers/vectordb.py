
from database.chroma import AsyncChromadbClient
from config import settings
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Dict, Any
from authorization.token_based import get_current_user
import asyncio


router = APIRouter(prefix='/vectordb',tags=["vectordb"])


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
async def insert_data(request: InsertRequest,current_user = Depends(get_current_user)):
    await chromadb_client.insert(
        query=request.query,
        metadatas=request.metadatas,
        documents=request.documents,
        ids=request.ids,
        collection_name=request.collection_name,
    )
    return {"message": "Data inserted successfully"}

@router.post("/query")
async def query_data(request: QueryRequest, current_user = Depends(get_current_user)):
    results = await chromadb_client.query(
        query=request.query,
        n_results=request.n_results,
        collection_name=request.collection_name,
    )
    return results

@router.get("/collections")
async def list_collections(current_user = Depends(get_current_user)):
    collections = await chromadb_client.list_collection()
    return {"collections": collections}

@router.delete("/collections/{collection_name}")
async def delete_collection(collection_name: str, current_user = Depends(get_current_user)):
    await chromadb_client.delete_collection(collection_name)
    return {"message": f"Collection {collection_name} deleted successfully"}
