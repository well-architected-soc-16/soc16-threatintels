"""Gerbang per sumber: cache, lalu pembatas kuota, lalu adapter (TASK-02 Tahap 3; Bab 5).

`SourceGateway` memenuhi Protocol `ReputationSource`, jadi `collect_sources` tidak berubah.
Membuatnya tidak melakukan apa pun (hanya menyimpan referensi engine); SEMUA akses cache, kuota,
dan jaringan terjadi di `fetch`, yang hanya dipanggil setelah `validate_ip` lolos.

Urutan di `fetch`: cache hit -> kembalikan (tanpa baris `source_calls`, tanpa kuota);
miss -> reservasi kuota (commit, lock dilepas) -> request di luar lock -> selesaikan baris ->
simpan ke cache bila statusnya boleh di-cache.
"""

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.services.sources import cache, quota
from app.services.sources._common import utc_now
from app.services.sources.base import (
    ReputationSource,
    SourceReason,
    SourceResult,
    SourceStatus,
)

logger = logging.getLogger(__name__)


class SourceGateway:
    def __init__(
        self,
        inner: ReputationSource,
        *,
        engine: Engine,
        mode: str,
        params_key: str,
        policy: quota.QuotaPolicy,
        ttl: cache.CacheTtl,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.name = inner.name
        self._inner = inner
        self._engine = engine
        self._mode = mode
        self._params_key = params_key
        self._policy = policy
        self._ttl = ttl
        # Satu jam untuk cek kedaluwarsa, `called_at`, dan `expires_at` (tidak bercampur dengan
        # jam adapter, yang hanya menentukan `retrieved_at`).
        self._clock = clock

    def fetch(self, ip: str) -> SourceResult:
        now = self._clock()

        with Session(self._engine) as session:
            hit = cache.lookup(
                session,
                source=self.name,
                ip=ip,
                params_key=self._params_key,
                mode=self._mode,
                now=now,
            )
        if hit is not None:
            return hit

        with Session(self._engine) as session, session.begin():
            call_id = quota.reserve(
                session,
                source=self.name,
                mode=self._mode,
                policy=self._policy,
                now=now,
            )
        # Transaksi (dan advisory lock) sudah dilepas: request tidak pernah berjalan di bawah lock.
        if call_id is None:
            return SourceResult(
                source=self.name,
                status=SourceStatus.SKIPPED,
                reason=SourceReason.QUOTA_INTERNAL,
                retrieved_at=now,
            )

        # Bila adapter melempar exception, baris reservasi dibiarkan tak selesai dan tetap dihitung.
        result = self._inner.fetch(ip)

        with Session(self._engine) as session, session.begin():
            quota.finalize(session, call_id, result)

        ttl = self._ttl.for_status(result.status)
        if ttl is None:
            return result
        expires_at = self._clock() + ttl
        try:
            with Session(self._engine) as session, session.begin():
                cache.store(
                    session,
                    result,
                    ip=ip,
                    params_key=self._params_key,
                    mode=self._mode,
                    expires_at=expires_at,
                    fallback_retrieved_at=now,
                )
        except Exception as exc:  # noqa: BLE001
            # Request live sudah berhasil dan kuotanya sudah terpakai: jangan buang hasilnya hanya
            # karena cache gagal ditulis. Kembalikan apa adanya, tanpa cache (`expires_at` null).
            # Log hanya nama sumber dan kelas exception (pesan bisa memuat data sensitif).
            logger.error(
                "gagal menyimpan cache sumber %s: %s", self.name, type(exc).__name__
            )
            return result
        return replace(result, expires_at=expires_at)
