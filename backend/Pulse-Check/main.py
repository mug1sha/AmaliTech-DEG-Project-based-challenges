from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone, timedelta
import asyncio

app = FastAPI(title="Pulse-Check API")

# Request model for creating a monitor
class MonitorCreate(BaseModel):
    id: str
    timeout: int
    alert_email: EmailStr

# In-memory storage (for demo purposes)
monitors = {}
tasks = {}


def now_utc():
    return datetime.now(timezone.utc)


def calculate_remaining_seconds(monitor_id: str):
    monitor = monitors[monitor_id]

    if monitor["status"] != "active":
        return 0

    deadline = monitor["deadline"]
    remaining = (deadline - now_utc()).total_seconds()

    return max(0, int(remaining))


async def countdown(monitor_id: str):
    timeout = monitors[monitor_id]["timeout"]

    await asyncio.sleep(timeout)

    if monitor_id in monitors and monitors[monitor_id]["status"] == "active":
        monitors[monitor_id]["status"] = "down"

        alert = {
            "ALERT": f"Device {monitor_id} is down!",
            "time": now_utc().isoformat()
        }

        print(alert) # Simulated alert system


def start_timer(monitor_id: str):
    if monitor_id in tasks:
        tasks[monitor_id].cancel()

    monitors[monitor_id]["deadline"] = now_utc() + timedelta(
        seconds=monitors[monitor_id]["timeout"]
    )

    tasks[monitor_id] = asyncio.create_task(countdown(monitor_id))


@app.post("/monitors", status_code=201)
async def create_monitor(monitor: MonitorCreate):
    monitors[monitor.id] = {
        "id": monitor.id,
        "timeout": monitor.timeout,
        "alert_email": monitor.alert_email,
        "status": "active",
        "created_at": now_utc().isoformat(),
        "last_heartbeat": None,
        "deadline": None
    }

    start_timer(monitor.id)

    return {
        "message": f"Monitor {monitor.id} created successfully",
        "status": "active",
        "remaining_seconds": calculate_remaining_seconds(monitor.id)
    }


@app.post("/monitors/{monitor_id}/heartbeat")
async def heartbeat(monitor_id: str):
    if monitor_id not in monitors:
        raise HTTPException(status_code=404, detail="Monitor not found")

    monitors[monitor_id]["status"] = "active"
    monitors[monitor_id]["last_heartbeat"] = now_utc().isoformat()

    start_timer(monitor_id)

    return {
        "message": f"Heartbeat received for {monitor_id}",
        "status": "active",
        "remaining_seconds": calculate_remaining_seconds(monitor_id)
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
        "status": "paused",
        "remaining_seconds": 0
    }


@app.get("/monitors/{monitor_id}/status")
async def get_monitor_status(monitor_id: str):
    if monitor_id not in monitors:
        raise HTTPException(status_code=404, detail="Monitor not found")

    monitor = monitors[monitor_id]

    return {
        "id": monitor["id"],
        "status": monitor["status"],
        "timeout": monitor["timeout"],
        "remaining_seconds": calculate_remaining_seconds(monitor_id),
        "last_heartbeat": monitor["last_heartbeat"],
        "alert_email": monitor["alert_email"]
    }


@app.get("/monitors/{monitor_id}")
async def get_monitor(monitor_id: str):
    if monitor_id not in monitors:
        raise HTTPException(status_code=404, detail="Monitor not found")

    monitor = monitors[monitor_id].copy()
    monitor["remaining_seconds"] = calculate_remaining_seconds(monitor_id)

    if monitor["deadline"]:
        monitor["deadline"] = monitor["deadline"].isoformat()

    return monitor


@app.get("/monitors")
async def get_all_monitors():
    result = {}

    for monitor_id, monitor in monitors.items():
        data = monitor.copy()
        data["remaining_seconds"] = calculate_remaining_seconds(monitor_id)

        if data["deadline"]:
            data["deadline"] = data["deadline"].isoformat()

        result[monitor_id] = data

    return result