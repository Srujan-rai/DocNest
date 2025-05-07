from fastapi import Depends, HTTPException, Header,APIRouter
from firebase_admin import auth as firebase_auth
from db import db  # your Prisma client

router = APIRouter()
async def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token header")

    id_token = authorization.split("Bearer ")[1]

    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        email = decoded_token.get("email")

        if not email:
            raise HTTPException(status_code=401, detail="No email in token")

        user = await db.user.find_unique(where={"email": email})
        if not user:
            raise HTTPException(status_code=403, detail="User not registered")

        return user  # You can also return custom dict with roles

    except Exception:
        raise HTTPException(status_code=401, detail="Token invalid or expired")

