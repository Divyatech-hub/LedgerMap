from fastapi import APIRouter

from ledgermap.api.routers import clients, exports, health, mappings, runs

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(clients.router, tags=["clients"])
api_router.include_router(runs.router, tags=["runs"])
api_router.include_router(mappings.router, tags=["mappings"])
api_router.include_router(exports.router, tags=["exports"])