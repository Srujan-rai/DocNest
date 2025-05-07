from fastapi import Request

# Dummy user context for development (assumes all requests are from admin)
async def get_current_user(request: Request):
    return {"id": 1, "email": "admin@example.com"}  # Replace with actual admin ID
