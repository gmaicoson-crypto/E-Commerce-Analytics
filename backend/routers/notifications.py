from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from dependencies import get_current_user
from models import Notification
from utils import success_response

router = APIRouter()


@router.get("/list", response_model=dict)
async def get_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=10000),
    is_read: bool = Query(None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get notifications list with pagination."""
    query = db.query(Notification)

    if is_read is not None:
        query = query.filter(Notification.is_read == (1 if is_read else 0))

    total = query.count()
    notifications = query.order_by(
        Notification.created_at.desc()
    ).offset((page - 1) * page_size).limit(page_size).all()

    notif_list = [
        {
            "id": n.id,
            "type": n.type.value if n.type else "Unknown",
            "title": n.title,
            "content": n.content,
            "is_read": bool(n.is_read),
            "created_at": n.created_at.isoformat() if n.created_at else None
        }
        for n in notifications
    ]

    return success_response({
        "data": notif_list,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size
        }
    })


@router.get("/unread-count", response_model=dict)
async def unread_count(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get count of unread notifications."""
    count = db.query(Notification).filter(Notification.is_read == 0).count()
    return success_response({"unread_count": count})


# 注意:/batch/* 必须在 /{notification_id}/... 之前注册,否则 FastAPI 会先用
#       /{notification_id} 的 int 校验吞掉 "batch" 字面量 → 422
@router.patch("/batch/read", response_model=dict)
async def mark_batch_as_read(
    request: dict,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark multiple notifications as read. ids=[] 表示全部未读标记为已读。"""
    notification_ids = request.get("notification_ids", [])

    if notification_ids:
        affected = db.query(Notification).filter(
            Notification.id.in_(notification_ids)
        ).update({"is_read": 1}, synchronize_session=False)
    else:
        # 兜底:没传 ids 时一次性标记全部未读
        affected = db.query(Notification).filter(
            Notification.is_read == 0
        ).update({"is_read": 1}, synchronize_session=False)
    db.commit()

    return success_response({
        "count": int(affected or 0)
    }, message="Notifications marked as read")


@router.delete("/batch", response_model=dict)
async def delete_batch(
    request: dict,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete multiple notifications."""
    notification_ids = request.get("notification_ids", [])

    if not notification_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="notification_ids required"
        )

    count = db.query(Notification).filter(
        Notification.id.in_(notification_ids)
    ).delete(synchronize_session=False)
    db.commit()

    return success_response({
        "count": count
    }, message="Notifications deleted")


@router.get("/stats/by-type", response_model=dict)
async def notification_stats_by_type(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get notification statistics by type."""
    notifications = db.query(Notification).all()

    type_stats = {}
    for notif in notifications:
        ntype = notif.type.value if notif.type else "Unknown"
        if ntype not in type_stats:
            type_stats[ntype] = {"total": 0, "read": 0, "unread": 0}
        type_stats[ntype]["total"] += 1
        if notif.is_read:
            type_stats[ntype]["read"] += 1
        else:
            type_stats[ntype]["unread"] += 1

    data = [
        {
            "type": ntype,
            "total": stats["total"],
            "read": stats["read"],
            "unread": stats["unread"]
        }
        for ntype, stats in type_stats.items()
    ]

    return success_response(data)


@router.get("/{notification_id}", response_model=dict)
async def get_notification(
    notification_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get single notification details."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id
    ).first()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    notif_data = {
        "id": notification.id,
        "type": notification.type.value if notification.type else "Unknown",
        "title": notification.title,
        "content": notification.content,
        "is_read": bool(notification.is_read),
        "created_at": notification.created_at.isoformat() if notification.created_at else None
    }

    return success_response(notif_data)


@router.patch("/{notification_id}/read", response_model=dict)
async def mark_as_read(
    notification_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark single notification as read."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id
    ).first()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    notification.is_read = 1
    db.commit()

    return success_response({
        "id": notification.id,
        "is_read": bool(notification.is_read)
    }, message="Notification marked as read")


@router.delete("/{notification_id}", response_model=dict)
async def delete_notification(
    notification_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a notification."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id
    ).first()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    db.delete(notification)
    db.commit()

    return success_response({
        "id": notification_id
    }, message="Notification deleted")
