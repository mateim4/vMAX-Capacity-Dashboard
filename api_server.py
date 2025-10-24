"""
FastAPI Web Server for VMAX Capacity Dashboard

This module provides a REST API and WebSocket server for the capacity
monitoring web application with Fluent UI 2 frontend.
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from config import load_config, UnisphereConfig
from vmax_collector import (
    VmaxCapacityCollector,
    ConnectionError as VmaxConnectionError,
    AuthenticationError,
    DataCollectionError
)
from data_models import CapacitySnapshot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="VMAX Capacity Dashboard API",
    description="REST API for Dell PowerMax/VMAX capacity monitoring",
    version="1.0.0"
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
current_snapshot: Optional[CapacitySnapshot] = None
collection_in_progress: bool = False
last_collection_time: Optional[str] = None
collection_error: Optional[str] = None
active_websockets: List[WebSocket] = []

# Pydantic models for API responses
class SystemCapacityResponse(BaseModel):
    array_id: str
    timestamp: str
    effective_used_capacity_gb: float
    max_effective_capacity_gb: float
    subscribed_capacity_gb: float
    total_usable_capacity_gb: float
    free_capacity_gb: float
    utilization_percent: float

class SrpCapacityResponse(BaseModel):
    array_id: str
    srp_id: str
    timestamp: str
    used_capacity_gb: float
    subscribed_capacity_gb: float
    total_managed_space_gb: float
    free_capacity_gb: float
    utilization_percent: float
    subscription_percent: float

class StorageGroupResponse(BaseModel):
    array_id: str
    storage_group_id: str
    timestamp: str
    capacity_gb: float
    num_volumes: int
    service_level: Optional[str]
    srp_name: Optional[str]
    compression_enabled: bool

class VolumeResponse(BaseModel):
    array_id: str
    volume_id: str
    volume_identifier: str
    timestamp: str
    capacity_gb: float
    allocated_percent: float
    storage_groups: List[str]
    wwn: Optional[str]
    emulation_type: Optional[str]

class StatusResponse(BaseModel):
    collection_in_progress: bool
    last_collection_time: Optional[str]
    has_data: bool
    error: Optional[str]
    array_id: Optional[str]

class CollectionRequest(BaseModel):
    force_refresh: bool = False


# Helper function to convert dataclass to dict
def dataclass_to_dict(obj) -> dict:
    """Convert dataclass to dictionary for JSON serialization."""
    if hasattr(obj, '__dataclass_fields__'):
        result = {}
        for field_name in obj.__dataclass_fields__:
            value = getattr(obj, field_name)
            if isinstance(value, list):
                result[field_name] = [dataclass_to_dict(item) for item in value]
            elif hasattr(value, '__dataclass_fields__'):
                result[field_name] = dataclass_to_dict(value)
            else:
                result[field_name] = value
        return result
    return obj


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()


# Background task for capacity collection
async def collect_capacity_data():
    """Background task to collect capacity data from VMAX array."""
    global current_snapshot, collection_in_progress, last_collection_time, collection_error
    
    collection_in_progress = True
    collection_error = None
    
    # Broadcast collection started
    await manager.broadcast({
        "type": "collection_started",
        "timestamp": datetime.now().isoformat()
    })
    
    try:
        logger.info("Starting capacity collection...")
        config = load_config("config.json")
        
        with VmaxCapacityCollector(
            host=config.host,
            port=config.port,
            username=config.username,
            password=config.password,
            verify_ssl=config.verify_ssl,
            array_id=config.array_id
        ) as collector:
            
            # Collect system data
            await manager.broadcast({
                "type": "collection_progress",
                "step": "system",
                "message": "Collecting system capacity..."
            })
            
            snapshot = collector.get_all_capacity_data(config.array_id)
            
            current_snapshot = snapshot
            last_collection_time = datetime.now().isoformat()
            collection_error = None
            
            logger.info("Capacity collection completed successfully")
            
            # Broadcast collection completed with data
            await manager.broadcast({
                "type": "collection_completed",
                "timestamp": last_collection_time,
                "summary": {
                    "array_id": snapshot.array_id,
                    "total_srps": snapshot.total_srps,
                    "total_storage_groups": snapshot.total_storage_groups,
                    "total_volumes": snapshot.total_volumes,
                    "system_utilization_percent": snapshot.system_capacity.utilization_percent
                }
            })
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Collection failed: {error_msg}")
        collection_error = error_msg
        
        await manager.broadcast({
            "type": "collection_error",
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        })
    
    finally:
        collection_in_progress = False


# API Endpoints

@app.get("/")
async def root():
    """Serve the React frontend."""
    frontend_path = Path("frontend/build/index.html")
    if frontend_path.exists():
        return FileResponse(frontend_path)
    return {"message": "VMAX Capacity Dashboard API", "status": "running"}


@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Get current collection status."""
    return StatusResponse(
        collection_in_progress=collection_in_progress,
        last_collection_time=last_collection_time,
        has_data=current_snapshot is not None,
        error=collection_error,
        array_id=current_snapshot.array_id if current_snapshot else None
    )


@app.post("/api/collect")
async def trigger_collection(request: CollectionRequest, background_tasks: BackgroundTasks):
    """Trigger a new capacity collection."""
    global collection_in_progress
    
    if collection_in_progress and not request.force_refresh:
        raise HTTPException(
            status_code=409,
            detail="Collection already in progress"
        )
    
    # Start collection in background
    background_tasks.add_task(collect_capacity_data)
    
    return {
        "status": "started",
        "message": "Capacity collection initiated",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/system")
async def get_system_capacity():
    """Get system-level capacity data."""
    if current_snapshot is None:
        raise HTTPException(status_code=404, detail="No data available. Run collection first.")
    
    return dataclass_to_dict(current_snapshot.system_capacity)


@app.get("/api/srps")
async def get_srp_capacities():
    """Get all SRP capacity data."""
    if current_snapshot is None:
        raise HTTPException(status_code=404, detail="No data available. Run collection first.")
    
    return [dataclass_to_dict(srp) for srp in current_snapshot.srp_capacities]


@app.get("/api/storage-groups")
async def get_storage_groups(
    service_level: Optional[str] = None,
    srp_name: Optional[str] = None,
    limit: Optional[int] = None
):
    """Get storage group capacity data with optional filtering."""
    if current_snapshot is None:
        raise HTTPException(status_code=404, detail="No data available. Run collection first.")
    
    storage_groups = current_snapshot.storage_group_capacities
    
    # Apply filters
    if service_level:
        storage_groups = [sg for sg in storage_groups if sg.service_level == service_level]
    
    if srp_name:
        storage_groups = [sg for sg in storage_groups if sg.srp_name == srp_name]
    
    # Sort by capacity (largest first)
    storage_groups = sorted(storage_groups, key=lambda x: x.capacity_gb, reverse=True)
    
    # Apply limit
    if limit:
        storage_groups = storage_groups[:limit]
    
    return [dataclass_to_dict(sg) for sg in storage_groups]


@app.get("/api/volumes")
async def get_volumes(
    storage_group: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = 0
):
    """Get volume capacity data with pagination and filtering."""
    if current_snapshot is None:
        raise HTTPException(status_code=404, detail="No data available. Run collection first.")
    
    volumes = current_snapshot.volume_capacities
    
    # Apply filter
    if storage_group:
        volumes = [v for v in volumes if storage_group in v.storage_groups]
    
    # Sort by capacity (largest first)
    volumes = sorted(volumes, key=lambda x: x.capacity_gb, reverse=True)
    
    total_count = len(volumes)
    
    # Apply pagination
    if limit:
        volumes = volumes[offset:offset + limit]
    
    return {
        "total": total_count,
        "offset": offset,
        "limit": limit,
        "items": [dataclass_to_dict(v) for v in volumes]
    }


@app.get("/api/summary")
async def get_summary():
    """Get high-level capacity summary."""
    if current_snapshot is None:
        raise HTTPException(status_code=404, detail="No data available. Run collection first.")
    
    return current_snapshot.summary()


@app.get("/api/trends/service-levels")
async def get_service_level_breakdown():
    """Get capacity breakdown by service level."""
    if current_snapshot is None:
        raise HTTPException(status_code=404, detail="No data available. Run collection first.")
    
    breakdown = {}
    for sg in current_snapshot.storage_group_capacities:
        slo = sg.service_level or "None"
        if slo not in breakdown:
            breakdown[slo] = {
                "service_level": slo,
                "count": 0,
                "total_capacity_gb": 0,
                "num_volumes": 0
            }
        breakdown[slo]["count"] += 1
        breakdown[slo]["total_capacity_gb"] += sg.capacity_gb
        breakdown[slo]["num_volumes"] += sg.num_volumes
    
    return list(breakdown.values())


@app.get("/api/trends/top-consumers")
async def get_top_consumers(limit: int = 10):
    """Get top storage groups by capacity."""
    if current_snapshot is None:
        raise HTTPException(status_code=404, detail="No data available. Run collection first.")
    
    top_sgs = sorted(
        current_snapshot.storage_group_capacities,
        key=lambda x: x.capacity_gb,
        reverse=True
    )[:limit]
    
    return [dataclass_to_dict(sg) for sg in top_sgs]


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    
    try:
        # Send initial status
        await websocket.send_json({
            "type": "connected",
            "status": {
                "collection_in_progress": collection_in_progress,
                "last_collection_time": last_collection_time,
                "has_data": current_snapshot is not None
            }
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle ping/pong for keep-alive
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "has_data": current_snapshot is not None
    }


# Serve static files for React frontend (production)
if Path("frontend/build").exists():
    app.mount("/static", StaticFiles(directory="frontend/build/static"), name="static")


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting VMAX Capacity Dashboard API Server...")
    logger.info("Access the dashboard at: http://localhost:8000")
    logger.info("API documentation at: http://localhost:8000/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
