from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.ai.provider import get_provider
from backend.app.api.deps import get_current_user
from backend.app.schemas.analyses import AnalysisRequest
from backend.app.services.analyses import analyze_text

router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.post("")
def create_analysis(
    payload: AnalysisRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    provider=Depends(get_provider),
):
    return analyze_text(payload, provider)