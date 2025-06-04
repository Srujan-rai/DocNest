from fastapi import APIRouter
import datetime

router = APIRouter()

@router.get("/", tags=["Health"])
async def root_health_check():
    return {"status": "ok", "message": "API is running"}

@router.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "timestamp": str(datetime.datetime.utcnow())
    }