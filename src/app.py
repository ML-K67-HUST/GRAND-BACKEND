
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from fastapi import Request
from pydantic import BaseModel
from typing import List
from routers import (
    socket,
    health_check,
    users,
    vectordb,
    nosqldb,
    tasks,
    authorize,
    conversation,
)
from starlette.middleware.sessions import SessionMiddleware
from config import settings

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)


app.include_router(health_check.router)
app.include_router(socket.router)
app.include_router(authorize.router)
app.include_router(users.router)
app.include_router(tasks.router)
app.include_router(vectordb.router)
app.include_router(nosqldb.router)
app.include_router(conversation.router)

# @app.post("/trigger_task")
# async def trigger_task(request: Request):
#     try:
#         data = await request.json()
#         task = data.get("task", [])
#         await socket.broadcast_task_added(task)
#         return {"status": "sent"}
#     except Exception as e:
#         return {"status": "failed", "error": str(e)}
class Task(BaseModel):
    userid: str
    taskid: str
    task_name: str
    task_description: str
    color: str
    start_time: int
    end_time: int
    status: str
    priority: int

@app.post("/trigger_task")
async def trigger_task(task: List[Task]):
    await socket.broadcast_task_added([t.dict() for t in task])
    return {"status": "sent"}

