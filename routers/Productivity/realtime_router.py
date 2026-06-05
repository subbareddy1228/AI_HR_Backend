from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import List
import json, asyncio, os
import redis.asyncio as aioredis
from jose import jwt, JWTError
from core.config import SECRET_KEY, ALGORITHM, REDIS_URL

router = APIRouter(prefix="/realtime", tags=["realtime"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()


redis_client = None

async def init_redis():
    global redis_client
    try:
        redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        print(" Connected to Redis")
    except Exception:
        print(" Redis not running — using in-memory fallback.")
        redis_client = None


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    #  JWT validation on connect
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        return

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        await websocket.close(code=4002)
        return

    # Accept connection
    await manager.connect(websocket)
    user_channel = f"stream:{email}"

    try:
        # Loop to receive messages (compressed or limited)
        while True:
            data = await websocket.receive_json()
            data["user"] = email
            data["timestamp"] = data.get("timestamp", None)

            # Publish to Redis or broadcast directly
            if redis_client:
                await redis_client.publish(user_channel, json.dumps(data))
            else:
                await manager.broadcast(data)

            #  Throttle frame rate (1 frame/second)
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print("WebSocket Error:", e)
        await websocket.close()


async def redis_subscriber():
    if not redis_client:
        return
    pubsub = redis_client.pubsub()
    await pubsub.psubscribe("stream:*")
    async for message in pubsub.listen():
        if message and message["type"] == "pmessage":
            data = json.loads(message["data"])
            await manager.broadcast(data)


@router.on_event("startup")
async def on_startup():
    await init_redis()
    if redis_client:
        asyncio.create_task(redis_subscriber())
