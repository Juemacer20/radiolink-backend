from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import links, ws
from app.database import create_tables

app = FastAPI(
    title="RadioLink API",
    description="Backend para orientacion de radioenlaces de microondas",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await create_tables()


app.include_router(links.router, prefix="/api/v1/links", tags=["Radioenlaces"])
app.include_router(ws.router, prefix="/ws", tags=["WebSocket"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "RadioLink API v1.0"}
