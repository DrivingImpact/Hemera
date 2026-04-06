"""Auth endpoints — user info and Clerk webhook."""
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from hemera.database import get_db
from hemera.dependencies import get_current_user
from hemera.services.clerk import ClerkUser
from hemera.models.user import User
from hemera.config import get_settings
import json

router = APIRouter()


def _verify_webhook_signature(request_body: bytes, headers: dict) -> bool:
    settings = get_settings()
    if not settings.clerk_webhook_secret:
        return True
    try:
        from svix.webhooks import Webhook
        wh = Webhook(settings.clerk_webhook_secret)
        wh.verify(request_body, headers)
        return True
    except Exception:
        return False


@router.get("/auth/me")
def get_me(current_user: ClerkUser = Depends(get_current_user)):
    return {
        "clerk_id": current_user.clerk_id,
        "email": current_user.email,
        "org_name": current_user.org_name,
        "role": current_user.role,
    }


@router.post("/webhooks/clerk")
async def clerk_webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    headers = dict(request.headers)
    if not _verify_webhook_signature(body, headers):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    payload = json.loads(body)
    event_type = payload.get("type", "")
    data = payload.get("data", {})
    clerk_id = data.get("id", "")
    emails = data.get("email_addresses", [])
    email = emails[0].get("email_address", "") if emails else ""
    metadata = data.get("public_metadata", {})
    org_name = metadata.get("org_name", "")
    role = metadata.get("role", "client")

    if event_type == "user.created":
        existing = db.query(User).filter(User.clerk_id == clerk_id).first()
        if not existing:
            user = User(clerk_id=clerk_id, email=email, org_name=org_name, role=role, is_admin=(role == "admin"))
            db.add(user)
            db.commit()
    elif event_type == "user.updated":
        user = db.query(User).filter(User.clerk_id == clerk_id).first()
        if user:
            user.email = email
            user.org_name = org_name
            user.role = role
            user.is_admin = (role == "admin")
            db.commit()
    elif event_type == "user.deleted":
        user = db.query(User).filter(User.clerk_id == clerk_id).first()
        if user:
            user.is_active = False
            db.commit()
    return {"status": "ok"}
