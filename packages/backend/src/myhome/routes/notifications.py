from fastapi import APIRouter

from ..models_notifications import Notification
from ..notifications import compute_notifications

router = APIRouter()


@router.get("/api/homes/{home_id}/notifications", response_model=list[Notification])
def get_notifications(home_id: str) -> list[Notification]:
    return compute_notifications(home_id)
