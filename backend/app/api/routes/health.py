from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="Check API availability")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
