from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends
from query_hub.conversation import *
from datetime import datetime
from authorization.token_based import get_current_user
from config import settings
router = APIRouter(prefix='/conversation',tags=["conversation"])

class QueryElement(BaseModel):
    userid :int
class HistoryElement(BaseModel):
    user : str
    assistant: str

class ConversationRequest(BaseModel):
    userid: int
    history: HistoryElement

@router.post("/query")
async def get_conver(query: QueryElement, current_user = Depends(get_current_user)):
    conversations = get_conversation(query.userid)
    return {
        "userid":query.userid,
        "history":conversations
    }

@router.post("/update")
async def insert_conver(convo:ConversationRequest, current_user = Depends(get_current_user)):
    try:
        created_at = datetime.now().timestamp()
        result = insert_conversation(
            userid=convo.userid,
            history={
                "created_at":created_at,
                "user": convo.history.user,
                "assistant": convo.history.assistant
            }
        )
        if not result:
            raise HTTPException(status_code=500, detail=f"Exception happened while update")
        return {
            "message":"Suck seed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Exception happened: {e}")

    