from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import clientes, movimientos, pedidos, inventario, pedidos_shein, auth, recargas, setting

@asynccontextmanager
async def lifespan(app: FastAPI):
    # init_db() (Base.metadata.create_all) ya NO se ejecuta aquí.
    # Alembic es la única fuente de verdad del esquema: el arranque
    # real depende de que `alembic upgrade head` ya se haya corrido
    # antes de levantar la app. init_db.py se conserva solo como
    # utilidad manual de desarrollo, no se invoca automáticamente.
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
app.include_router(inventario.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(recargas.router, prefix="/api/v1")
app.include_router(setting.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"status": "ok", "sistema": "pos-boutique", "version": "0.1.0"}

@app.get("/ping")
def ping():
    return {"mensaje": "pong desde pos-boutique"}
