from fastapi import FastAPI, Depends, WebSocket, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any

from .routers import health, alerts, devices, flows, metrics, thresholds
from .middleware.logging import LoggingMiddleware
from .websockets.manager import ConnectionManager

app = FastAPI(
    title="Smart Home IDS API",
    description="Backend API for the Smart Home Intrusion Detection System",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)

# Routers
app.include_router(health.router, prefix="/api")
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(devices.router, prefix="/api/devices", tags=["devices"])
app.include_router(flows.router, prefix="/api/flows", tags=["flows"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
app.include_router(thresholds.router, prefix="/api/thresholds", tags=["thresholds"])

# Websockets
manager = ConnectionManager()

@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming websocket messages if needed
    except Exception as e:
        manager.disconnect(websocket)
