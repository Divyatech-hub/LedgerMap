from fastapi import FastAPI

from ledgermap.api.router import api_router

app = FastAPI(title="LedgerMap", version="0.1.0")
app.include_router(api_router)