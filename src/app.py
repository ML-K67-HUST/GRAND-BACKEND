
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from routers import (
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



app.include_router(authorize.router)
app.include_router(users.router)
app.include_router(tasks.router)
app.include_router(vectordb.router)
app.include_router(nosqldb.router)
app.include_router(conversation.router)


