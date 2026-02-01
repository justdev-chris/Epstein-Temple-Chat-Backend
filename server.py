# server.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
import json
from uuid import uuid4
from datetime import datetime
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for Swift app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.message_history: List[Dict] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Send history to new connection
        for msg in self.message_history[-50:]:
            await websocket.send_json(msg)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: Dict):
        self.message_history.append(message)
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                self.disconnect(connection)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Receive from Swift/iOS
            data = await websocket.receive_json()
            
            # Build response matching Swift's Message struct
            response = {
                "id": str(uuid4()),
                "user": data.get("user", "Anon"),
                "text": data.get("text", ""),
                "timestamp": datetime.now().isoformat() + "Z"
            }
            
            # Broadcast to everyone (including sender)
            await manager.broadcast(response)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"Error: {e}")
        manager.disconnect(websocket)

@app.get("/")
def read_root():
    return {"status": "Temple Chat WS", "connections": len(manager.active_connections)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
