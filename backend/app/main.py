from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.init_db import init_db
from app.api.v1.endpoints import clientes, movimientos, pedidos, pedidos_shein, auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="pos-boutique",
    description="Sistema de gestión POS para tienda de ropa con crédito local",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clientes.router, prefix="/api/v1")
app.include_router(movimientos.router, prefix="/api/v1")
app.include_router(pedidos.router, prefix="/api/v1")
app.include_router(pedidos_shein.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")

@app.get("/")
def root():
    return {"status": "ok", "sistema": "pos-boutique", "version": "0.1.0"}

@app.get("/ping")
def ping():
    return {"mensaje": "pong desde pos-boutique"}
