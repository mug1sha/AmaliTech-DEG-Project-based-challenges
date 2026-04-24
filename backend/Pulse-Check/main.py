from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from datetime import datetime
import asyncio

app = FastAPI(title="Pulse-Check API")


class MonitorCreate(BaseModel):
    id: str
    timeout: int
    alert_email: EmailStr


monitors = {}
tasks = {}


async def countdown(monitor_id: str):
    timeout = monitors[monitor_id]["timeout"]
    await asyncio.sleep(timeout)

    if monitors[monitor_id]["status"] == "active":
        monitors[monitor_id]["status"] = "down"

        alert = {
            "ALERT": f"Device {monitor_id} is down!",
            "time": datetime.utcnow().isoformat()
        }

        print(alert)


def start_timer(monitor_id: str):
    if monitor_id in tasks:
        tasks[monitor_id].cancel()

    tasks[monitor_id] = asyncio.create_task(countdown(monitor_id))

@app.get("/")
def root():
    return {"message": "Idempotency Gateway API is running"}

@app.post("/monitors", status_code=201)
async def create_monitor(monitor: MonitorCreate):
    monitors[monitor.id] = {
        "id": monitor.id,
        "timeout": monitor.timeout,
        "alert_email": monitor.alert_email,
        "status": "active",
        "created_at": datetime.utcnow().isoformat()
    }

    start_timer(monitor.id)

    return {
        "message": f"Monitor {monitor.id} created successfully",
        "status": "active"
    }


@app.post("/monitors/{monitor_id}/heartbeat")
async def heartbeat(monitor_id: str):
    if monitor_id not in monitors:
        raise HTTPException(status_code=404, detail="Monitor not found")

    monitors[monitor_id]["status"] = "active"
    monitors[monitor_id]["last_heartbeat"] = datetime.utcnow().isoformat()

    start_timer(monitor_id)

    return {
        "message": f"Heartbeat received for {monitor_id}",
        "status": "active"
    }


@app.post("/monitors/{monitor_id}/pause")
async def pause_monitor(monitor_id: str):
    if monitor_id not in monitors:
        raise HTTPException(status_code=404, detail="Monitor not found")

    monitors[monitor_id]["status"] = "paused"

    if monitor_id in tasks:
        tasks[monitor_id].cancel()

    return {
        "message": f"Monitor {monitor_id} paused",
        "status": "paused"
    }


@app.get("/monitors/{monitor_id}")
async def get_monitor(monitor_id: str):
    if monitor_id not in monitors:
        raise HTTPException(status_code=404, detail="Monitor not found")

    return monitors[monitor_id]


@app.get("/monitors")
async def get_all_monitors():
    return monitors