from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import nodes, artifacts, tree, access
from db import db


app = FastAPI()

@app.on_event("startup")
async def startup():
    await db.connect()

@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tree.router)
app.include_router(nodes.router)
app.include_router(artifacts.router)
app.include_router(access.router)