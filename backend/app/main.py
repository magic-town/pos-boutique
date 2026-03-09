from fastapi import FastAPI
from app.db.init_db import init_db

app = FastAPI(
    title="pos-boutique",
    description="Sistema de gestión POS para tienda de ropa con crédito local",
    version="0.1.0"
)

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/")
def root():
    return {"status": "ok", "sistema": "pos-boutique", "version": "0.1.0"}
