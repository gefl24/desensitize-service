import os
from fastapi import Header, HTTPException


API_KEY = os.getenv("API_KEY", "").strip()


def require_api_key(x_api_key: str | None = Header(default=None)):
    if not API_KEY:
        return True
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")
    return True
