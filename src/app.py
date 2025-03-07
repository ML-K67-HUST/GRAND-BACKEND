
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from routers import (
    vectordb,
    nosqldb,
    sqldb
)

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




app.include_router(vectordb.router)
app.include_router(nosqldb.router)
app.include_router(sqldb.router)
