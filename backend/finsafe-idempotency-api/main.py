from fastapi import FastAPI, Header, HTTPException, Response
from pydantic import BaseModel
import asyncio
import hashlib
import json

app = FastAPI(title="FinSafe Idempotency Layer")

idempotency_store = {}
locks = {}


class PaymentRequest(BaseModel):
    amount: float
    currency: str


def hash_payload(payload: dict) -> str:
    payload_string = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(payload_string.encode()).hexdigest()


@app.post("/process-payment")
async def process_payment(
    payment: PaymentRequest,
    response: Response,
    idempotency_key: str = Header(None, alias="Idempotency-Key")
):
    if not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key header is required."
        )

    payload = payment.model_dump()
    payload_hash = hash_payload(payload)

    if idempotency_key not in locks:
        locks[idempotency_key] = asyncio.Lock()

    async with locks[idempotency_key]:

        if idempotency_key in idempotency_store:
            saved = idempotency_store[idempotency_key]

            if saved["payload_hash"] != payload_hash:
                raise HTTPException(
                    status_code=409,
                    detail="Idempotency key already used for a different request body."
                )

            response.headers["X-Cache-Hit"] = "true"
            response.status_code = saved["status_code"]
            return saved["body"]

        await asyncio.sleep(2)

        result = {
            "message": f"Charged {payment.amount:g} {payment.currency}",
            "status": "success"
        }

        idempotency_store[idempotency_key] = {
            "payload_hash": payload_hash,
            "status_code": 201,
            "body": result
        }

        response.status_code = 201
        response.headers["X-Cache-Hit"] = "false"
        return result