from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from config import settings
from database.mongodb import MongoManager
from bson import ObjectId
from authorization.token_based import get_current_user
from config import settings

def convert_objectid(doc):
    """Chuyển đổi ObjectId trong document thành string"""
    if isinstance(doc, list):
        return [convert_objectid(d) for d in doc]
    if isinstance(doc, dict):
        doc["_id"] = str(doc["_id"])  
        return doc
    return doc

router = APIRouter(prefix='/nosqldb',tags=["analysis"])

mongo_client = MongoManager("TIMENEST")

class Knowledge(BaseModel):
    url: str
    title: str
    detail: str
    answer: str

@router.get("/knowledges/query")
def get_knowdlege_info(current_user = Depends(get_current_user)):

    knowledge = mongo_client.find(
        "knowledge"
    )

    return {
        "status":"sucess",
        "content":convert_objectid(knowledge)
    }

@router.post("/knowledges/insert")
def get_knowdlege_info(knowdlegde:Knowledge, current_user = Depends(get_current_user)):
    try:
        mongo_client.insert_one(
            "knowledge",
            {
                'url':knowdlegde.url,
                'title':knowdlegde.title,
                'detail':knowdlegde.detail,
                'answer':knowdlegde.answer
            }
        )
        return {
            "status":"sucess",
            "content":knowdlegde
        }
    except Exception as e:
        print('exception ',e)
        return {
            "status":"failed",
            "exception":e
        }

   
