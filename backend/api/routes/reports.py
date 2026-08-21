"""Reports & statistics"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import Alert, Child, SearchLog, get_db

router = APIRouter()


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    total   = (await db.execute(select(func.count(Child.id)))).scalar() or 0
    missing = (await db.execute(select(func.count(Child.id)).where(Child.status == "missing"))).scalar() or 0
    found   = (await db.execute(select(func.count(Child.id)).where(Child.status == "found"))).scalar() or 0
    alerts  = (await db.execute(select(func.count(Alert.id)))).scalar() or 0
    searches= (await db.execute(select(func.count(SearchLog.id)))).scalar() or 0

    return {
        "total_registered":  total,
        "currently_missing": missing,
        "found":             found,
        "total_alerts":      alerts,
        "total_searches":    searches,
    }
