"""Smoke test sumber reputasi dengan API NYATA (TASK-02 Tahap 4). Dijalankan manual, bukan bagian pytest.

Jalankan (setelah SOURCES_MODE=live dan kedua file key terisi, lihat README):
    python -m scripts.smoke_sources --ip 118.25.6.39

Skrip ini MEMAKAI KUOTA BERSAMA TIM: satu cek memakai 1 kuota AbuseIPDB dan 1 kuota VirusTotal
(VirusTotal hanya 4 per menit). Jangan mengulanginya berturut-turut. Panggilan lewat
`SourceGateway` yang sama dengan API, jadi ikut terhitung limiter, tercatat di `source_calls`,
dan cek kedua untuk IP yang sama dijawab dari cache (tanpa request).

Keluaran hanya memuat hasil yang sudah dipetakan adapter (status, reason, skor, ringkasan bukti,
durasi, sisa kuota). Key, header request, dan teks exception tidak pernah dicetak.
"""

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import datetime
from typing import TextIO

from app.core.config import get_settings
from app.db.session import get_engine
from app.services.ip_validation import validate_ip
from app.services.sources.base import ReputationSource, SourceResult, SourceStatus
from app.services.sources.factory import build_gateways

DEFAULT_IP = "118.25.6.39"
# Hasil yang berarti sumber menjawab dengan benar. Selain ini (ERROR, SKIPPED, ...) skrip keluar 1.
HEALTHY_STATUSES = frozenset(
    {
        SourceStatus.OK_SIGNAL,
        SourceStatus.OK_NO_SIGNAL,
        SourceStatus.NO_RECORD,
        SourceStatus.INSUFFICIENT_DATA,
    }
)

EXIT_OK = 0
EXIT_SOURCE_PROBLEM = 1
EXIT_REFUSED = 2


def _show(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def print_result(result: SourceResult, out: TextIO) -> None:
    rows = [
        ("http_status", "-" if result.from_cache else _show(result.http_status)),
        ("status", result.status.value),
        ("reason", _show(result.reason.value if result.reason else None)),
        ("skor_ternormalisasi", _show(result.normalized_score)),
        ("durasi_ms", _show(result.duration_ms)),
        ("rate_limit_remaining", _show(result.rate_limit_remaining)),
        ("rate_limit_reset", _show(result.rate_limit_reset)),
        ("retry_after_detik", _show(result.retry_after_seconds)),
        ("dari_cache", "ya (tanpa request)" if result.from_cache else "tidak"),
        ("flags", ", ".join(result.flags) or "-"),
        ("waktu_sumber", _show(result.source_time)),
        ("bukti", json.dumps(result.evidence_summary, default=str, sort_keys=True)),
    ]
    print(f"[{result.source}]", file=out)
    for label, value in rows:
        print(f"  {label:<21}: {value}", file=out)


def run(ip: str, gateways: Sequence[ReputationSource], out: TextIO) -> int:
    """Panggil tiap gateway untuk `ip` dan cetak hasilnya. Mengembalikan exit code."""
    print("Smoke test sumber reputasi", file=out)
    print(f"ip: {ip}", file=out)
    problems = 0
    for gateway in gateways:
        print(file=out)
        try:
            result = gateway.fetch(ip)
        except Exception as exc:  # noqa: BLE001
            # Hanya nama kelas: pesan exception bisa memuat detail koneksi atau header.
            print(f"[{gateway.name}]", file=out)
            print(f"  gagal tak terduga: {type(exc).__name__}", file=out)
            problems += 1
            continue
        print_result(result, out)
        if result.status not in HEALTHY_STATUSES:
            problems += 1
    print(file=out)
    if problems:
        print(f"{problems} sumber bermasalah.", file=out)
        return EXIT_SOURCE_PROBLEM
    print("Semua sumber menjawab.", file=out)
    return EXIT_OK


def main(argv: Sequence[str] | None = None, out: TextIO | None = None) -> int:
    out = out or sys.stdout
    parser = argparse.ArgumentParser(
        description="Smoke test AbuseIPDB dan VirusTotal dengan API nyata (memakai kuota bersama)."
    )
    parser.add_argument("--ip", default=DEFAULT_IP, help="satu IPv4 publik")
    args = parser.parse_args(argv)

    # Input ditolak tidak boleh memicu request, akses cache, atau kuota.
    check = validate_ip(args.ip)
    if not check.valid or check.ip is None:
        reason = check.reason_code.value if check.reason_code else "INPUT_DITOLAK"
        print(f"IP ditolak ({reason}); tidak ada request yang dikirim.", file=out)
        return EXIT_REFUSED

    # Mode mock bukan bukti API nyata dan datanya simulasi: tolak, jangan diam-diam lanjut.
    if get_settings().sources_mode != "live":
        print(
            "SOURCES_MODE bukan 'live'; skrip ini hanya untuk API nyata. "
            "Lihat README, bagian mengaktifkan mode live.",
            file=out,
        )
        return EXIT_REFUSED

    return run(check.ip, build_gateways(get_engine()), out)


if __name__ == "__main__":
    sys.exit(main())
