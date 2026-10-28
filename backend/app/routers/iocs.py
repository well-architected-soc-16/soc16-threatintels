from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, DbSession, require_misp_permission
from app.models import IocSubmission, IpCheck, User
from app.schemas.common import FORBIDDEN, UNAUTHORIZED, ErrorResponse
from app.schemas.ioc import IocDuplicate, IocOut, IocPage, IocSubmit
from app.services import audit
from app.services.misp import MispClient, SubmissionResult, get_misp_client

MispUser = Annotated[User, Depends(require_misp_permission)]

router = APIRouter(prefix="/iocs", tags=["iocs"], responses=UNAUTHORIZED)


def _find_existing(db: Session, check_id: int) -> IocSubmission | None:
    return db.scalar(select(IocSubmission).where(IocSubmission.check_id == check_id))


def _failure_message(exc: Exception) -> str:
    # Pesan exception pihak ketiga bisa memuat URL/kredensial; simpan hanya nama kelasnya.
    return f"Gagal mengirim ke MISP ({type(exc).__name__})"


def _duplicate(
    request: Request, db: Session, user: User, existing: IocSubmission
) -> JSONResponse:
    audit.record(
        db,
        action="ioc_submit_duplicate",
        result="denied",
        actor_username=user.username,
        target=existing.ip,
        detail={"check_id": existing.check_id, "submission_id": existing.id},
        ip_address=audit.client_ip(request),
    )
    db.commit()
    body = IocDuplicate(
        detail="Check ini sudah pernah dikirim ke MISP", submission_id=existing.id
    )
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=body.model_dump())


@router.post(
    "/misp",
    response_model=IocOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        **FORBIDDEN,
        200: {
            "model": IocOut,
            "description": "Pengiriman ulang atas submission `failed`",
        },
        404: {"model": ErrorResponse, "description": "Check tidak ditemukan"},
        409: {
            "model": IocDuplicate,
            "description": "Check sudah pernah dikirim; berisi id submission yang ada",
        },
        422: {
            "description": "Alasan kosong/kurang dari 10 karakter, atau check "
            "berstatus INPUT_DITOLAK",
        },
        501: {
            "model": IocOut,
            "description": "MISP_MODE=live belum diimplementasikan; "
            "submission tersimpan sebagai `failed`",
        },
        502: {
            "model": IocOut,
            "description": "Pengiriman ke MISP gagal; submission tersimpan sebagai `failed`",
        },
    },
)
def submit_ioc(
    body: IocSubmit,
    request: Request,
    response: Response,
    user: MispUser,
    db: DbSession,
    misp: Annotated[MispClient, Depends(get_misp_client)],
) -> IocSubmission | JSONResponse:
    check = db.get(IpCheck, body.check_id)
    if check is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cek tidak ditemukan"
        )
    if check.assessment_status == "INPUT_DITOLAK":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Cek dengan input ditolak tidak boleh dikirim ke MISP",
        )

    existing = _find_existing(db, check.id)
    if existing is not None and existing.status != "failed":
        return _duplicate(request, db, user, existing)

    is_retry = existing is not None
    if existing is None:
        # Klaim dulu: UNIQUE(check_id) menjamin hanya satu request yang lolos,
        # termasuk saat dua klik datang bersamaan.
        submission = IocSubmission(
            check_id=check.id,
            ip=check.ip,
            reason=body.reason,
            tags=body.tags,
            status="pending",
            submitted_by=user.username,
        )
        db.add(submission)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            winner = _find_existing(db, check.id)
            if winner is None:
                raise
            return _duplicate(request, db, user, winner)
    else:
        # Percobaan ulang atas submission yang gagal memakai baris yang sama (tidak
        # menggandakan data). Transisi failed -> pending adalah satu UPDATE bersyarat
        # (WHERE status = 'failed'): di antara request yang bersamaan hanya satu yang
        # mendapat rowcount 1; yang lain melihat status sudah berubah dan menerima 409.
        claimed = db.execute(
            update(IocSubmission)
            .where(IocSubmission.id == existing.id, IocSubmission.status == "failed")
            .values(
                status="pending",
                error_message=None,
                reason=body.reason,
                tags=body.tags,
                submitted_by=user.username,
            )
        ).rowcount
        if claimed != 1:
            db.rollback()
            db.refresh(existing)
            return _duplicate(request, db, user, existing)
        # Audit ikut transaksi yang sama dengan klaim: retry yang lolos selalu tercatat.
        audit.record(
            db,
            action="ioc_submit_retry",
            result="success",
            actor_username=user.username,
            target=check.ip,
            detail={
                "check_id": check.id,
                "submission_id": existing.id,
                "previous_status": "failed",
            },
            ip_address=audit.client_ip(request),
        )
        db.commit()
        db.refresh(existing)
        submission = existing
        response.status_code = status.HTTP_200_OK

    failure_http_status = status.HTTP_502_BAD_GATEWAY
    try:
        result = misp.submit_indicator(check.ip, body.reason, body.tags, user.username)
    except NotImplementedError as exc:
        # MISP_MODE=live belum ada: bukan error server, fiturnya memang belum tersedia.
        failure_http_status = status.HTTP_501_NOT_IMPLEMENTED
        result = SubmissionResult(status="failed", error_message=str(exc))
    except Exception as exc:  # noqa: BLE001
        # Klien MISP (pihak ketiga) bisa melempar apa saja; apa pun yang gagal harus
        # tersimpan sebagai `failed`, bukan menjadi 500 yang meninggalkan baris `pending`.
        result = SubmissionResult(status="failed", error_message=_failure_message(exc))

    submission.status = result.status
    submission.misp_event_uuid = (
        result.misp_event_uuid if result.status != "failed" else None
    )
    submission.error_message = (result.error_message or "")[:500] or None
    if result.status == "failed" and not submission.error_message:
        submission.error_message = "Gagal mengirim ke MISP"
    audit.record(
        db,
        action="ioc_submit",
        result="error" if result.status == "failed" else "success",
        actor_username=user.username,
        target=check.ip,
        detail={
            "check_id": check.id,
            "submission_id": submission.id,
            "status": submission.status,
            "retry": is_retry,
        },
        ip_address=audit.client_ip(request),
    )
    db.commit()
    db.refresh(submission)

    if submission.status == "failed":
        # Kegagalan tidak boleh tampil sebagai sukses.
        return JSONResponse(
            status_code=failure_http_status,
            content=IocOut.model_validate(submission).model_dump(mode="json"),
        )
    return submission


@router.get("", response_model=IocPage)
def list_iocs(
    _: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> IocPage:
    total = db.scalar(select(func.count()).select_from(IocSubmission)) or 0
    rows = db.scalars(
        select(IocSubmission)
        .order_by(IocSubmission.submitted_at.desc(), IocSubmission.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return IocPage(
        items=[IocOut.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
