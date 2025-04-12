from fastapi import APIRouter, WebSocket
import asyncio

router = APIRouter()
connected_clients = []

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            await asyncio.sleep(1)
    except:
        pass
    finally:
        connected_clients.remove(websocket)

async def broadcast_task_added(task: list[dict]):
    for client in connected_clients[:]:
        try:
            await client.send_json(
                {
                    "type": "TASK_ADDED", 
                    "task":task
                }
            )
        except:
            connected_clients.remove(client)

