"""Membuat ulang berkas kontrak backend-*.json dari kode backend yang SEBENARNYA (adapter mock + assess + skema).

Berjalan di dalam kontainer `api` (kode backend ada di image), TANPA database dan TANPA jaringan.
Ini BUKAN uji end-to-end: gateway cache/kuota dan router dilewati, jadi `expires_at` null dan `from_cache` false.
Datanya fiktif: adapter mock memakai tabel IP demo TASK-02. Tidak membaca .env atau secrets/.

Pakai dari root repo (fish):

    docker compose exec -T api python - mock < frontend/src/testing/gen_backend_samples.py \
        > frontend/src/testing/backend-mock-samples.json
    docker compose exec -T api python - rejected < frontend/src/testing/gen_backend_samples.py \
        > frontend/src/testing/backend-rejected-samples.json

Setelah itu jalankan `npm test` di frontend/: uji kontrak (src/testing/contract.test.tsx) akan gagal bila
skema backend berubah sehingga tampilan atau penjaga bentuk perlu disesuaikan.
"""

import json
import sys
from datetime import UTC, datetime

from app.schemas.check import CheckOut, CheckRejected
from app.services import ip_checks
from app.services.ip_validation import validate_ip
from app.services.sources.mock import DEMO_SCENARIOS, MockSource

# Waktu tetap supaya keluaran deterministik: 2026-11-03 10:00 WIB.
FIXED = datetime(2026, 11, 3, 3, 0, 0, tzinfo=UTC)
REJECTED_INPUTS = ["10.10.50.10", "127.0.0.1", "2001:db8::1", "abc"]


def mock_samples() -> list[dict]:
    sources = [
        MockSource("abuseipdb", clock=lambda: FIXED),
        MockSource("virustotal", clock=lambda: FIXED),
    ]
    samples = []
    for number, ip in enumerate(DEMO_SCENARIOS, start=1):
        results = ip_checks.collect_sources(ip, sources)
        assessment = ip_checks.assess(results)
        check = CheckOut(
            id=number,
            ip=ip,
            assessment_status=assessment.assessment_status,
            risk_score=assessment.risk_score,
            scoring_version=ip_checks.SCORING_VERSION,
            coverage=assessment.coverage,
            flags=assessment.flags,
            sources=[ip_checks.to_stored(r) for r in results],
            checked_by="contoh",
            checked_at=FIXED,
        )
        samples.append(json.loads(check.model_dump_json()))
    return samples


def rejected_samples() -> dict[str, dict]:
    out = {}
    for raw in REJECTED_INPUTS:
        verdict = validate_ip(raw)
        assert not verdict.valid, raw
        body = CheckRejected(reason_code=verdict.reason_code, message=verdict.message)
        out[raw] = json.loads(body.model_dump_json())
    return out


MODES = {"mock": mock_samples, "rejected": rejected_samples}

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in MODES:
        sys.exit(f"mode harus salah satu dari: {', '.join(MODES)}")
    print(json.dumps(MODES[mode](), indent=2, ensure_ascii=False))
