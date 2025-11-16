from fastapi import APIRouter
from .auth import auth, ping
from .items import item


router = APIRouter()
router.include_router(ping.router, prefix="", tags=["ping"])
router.include_router(auth.router, prefix="", tags=["auth"])
router.include_router(item.router, prefix="/items", tags=["items"])