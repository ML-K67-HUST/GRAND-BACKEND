from fastapi import APIRouter
router = APIRouter(prefix='/health_check', tags=["ping"])


@router.get("/")
def health_check():
    return {
        "status":"ok"
    }