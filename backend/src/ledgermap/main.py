from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ledgermap.api.router import api_router

app = FastAPI(title="LedgerMap", version="0.1.0")

# Dev-only: allow the local Vite dev server to call the API directly.
# Tighten this to a configured origin allowlist before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)