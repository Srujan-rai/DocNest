from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import nodes, artifacts, tree, access, users, uploads,auth_routes,activity
from db import db  
from contextlib import asynccontextmanager
from firebase_setup import credentials

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🔌 Connecting to Prisma...")
    await db.connect()
    print("✅ Prisma connected.")

    yield  # ⏳ Run the application

    print("🔌 Disconnecting Prisma...")
    await db.disconnect()
    print("✅ Prisma disconnected.")

# FastAPI app with modern lifespan handler
app = FastAPI(lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict this later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include your routers
app.include_router(tree.router)
app.include_router(nodes.router)
app.include_router(artifacts.router)
app.include_router(access.router)
app.include_router(users.router)
app.include_router(uploads.router)
app.include_router(auth_routes.router)
app.include_router(activity.router)