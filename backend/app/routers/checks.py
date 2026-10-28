from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models import IpCheck, Role, User
from app.schemas.check import CheckCreate, CheckOut, CheckPage, CheckRejected
from app.schemas.common import FORBIDDEN, UNAUTHORIZED, ErrorResponse
from app.services import audit, ip_checks
from app.services.ip_validation import validate_ip

CheckWriter = Annotated[User, Depends(require_roles(Role.ADMIN, Role.ANALYST))]

router = APIRouter(prefix="/checks", tags=["checks"], responses=UNAUTHORIZED)


@router.post(
    "",
    response_model=CheckOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        **FORBIDDEN,
        422: {
            "model": CheckRejected,
            "description": "Input ditolak (assessment_status INPUT_DITOLAK); "
            "tidak ada request keluar yang dilakukan. Body yang tidak lengkap "
            "memakai format 422 standar FastAPI.",
        },
    },
)
def create_check(
    body: CheckCreate, request: Request, user: CheckWriter, db: DbSession
) -> IpCheck | JSONResponse:
    validation = validate_ip(body.ip)

    if not validation.valid:
        # Berhenti di sini: input yang ditolak tidak boleh memicu request keluar.
        audit.record(
            db,
            action="ip_check_rejected",
            result="denied",
            actor_username=user.username,
            target=body.ip[:64],
            detail={"reason_code": validation.reason_code.value},
            ip_address=audit.client_ip(request),
        )
        db.commit()
        rejected = CheckRejected(
            reason_code=validation.reason_code, message=validation.message
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=rejected.model_dump(mode="json"),
        )

    sources = ip_checks.collect_sources(validation.ip)
    assessment_status, coverage, risk_score = ip_checks.assess(sources)
    check = IpCheck(
        ip=validation.ip,
        assessment_status=assessment_status,
        risk_score=risk_score,
        scoring_version=ip_checks.SCORING_VERSION,
        coverage=coverage,
        flags=[],
        sources=sources,
        checked_by=user.username,
    )
    db.add(check)
    db.flush()
    audit.record(
        db,
        action="ip_check",
        result="success",
        actor_username=user.username,
        target=check.ip,
        detail={"check_id": check.id, "assessment_status": assessment_status},
        ip_address=audit.client_ip(request),
    )
    db.commit()
    db.refresh(check)
    return check


@router.get("", response_model=CheckPage)
def list_checks(
    _: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CheckPage:
    total = db.scalar(select(func.count()).select_from(IpCheck)) or 0
    rows = db.scalars(
        select(IpCheck)
        .order_by(IpCheck.checked_at.desc(), IpCheck.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return CheckPage(
        items=[CheckOut.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{check_id}",
    response_model=CheckOut,
    responses={404: {"model": ErrorResponse, "description": "Cek tidak ditemukan"}},
)
def get_check(check_id: int, _: CurrentUser, db: DbSession) -> IpCheck:
    check = db.get(IpCheck, check_id)
    if check is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cek tidak ditemukan"
        )
    return check
