"""Aturan `SourceResult` (TASK-02 Tahap 1): `reason` wajib untuk ERROR dan SKIPPED, null untuk lain.

Bab 3 dokumen riset: "SKIPPED; nilai null; sertakan alasan".
"""

import pytest

from app.services.sources.base import (
    REASON_REQUIRED_STATUSES,
    SourceReason,
    SourceResult,
    SourceStatus,
)

NEEDS_REASON = [SourceStatus.ERROR, SourceStatus.SKIPPED]
NO_REASON = [s for s in SourceStatus if s not in NEEDS_REASON]


def test_status_yang_mewajibkan_reason_adalah_error_dan_skipped():
    assert REASON_REQUIRED_STATUSES == frozenset(NEEDS_REASON)


@pytest.mark.parametrize("status", NEEDS_REASON)
def test_error_dan_skipped_tanpa_reason_ditolak(status):
    with pytest.raises(ValueError, match="wajib menyertakan reason"):
        SourceResult(source="abuseipdb", status=status)


@pytest.mark.parametrize("status", NO_REASON)
@pytest.mark.parametrize("reason", [SourceReason.TIMEOUT, SourceReason.QUOTA_INTERNAL])
def test_status_lain_dengan_reason_ditolak(status, reason):
    with pytest.raises(ValueError, match="tidak boleh membawa reason"):
        SourceResult(source="abuseipdb", status=status, reason=reason)


@pytest.mark.parametrize("status", NO_REASON)
def test_status_lain_tanpa_reason_diterima(status):
    result = SourceResult(source="virustotal", status=status)

    assert result.reason is None


@pytest.mark.parametrize(
    "reason",
    [SourceReason.ADAPTER_NOT_IMPLEMENTED, SourceReason.QUOTA_INTERNAL],
)
def test_skipped_dengan_alasan_diterima_dan_tanpa_skor(reason):
    result = SourceResult(
        source="virustotal", status=SourceStatus.SKIPPED, reason=reason
    )

    assert result.reason is reason
    assert result.normalized_score is None


@pytest.mark.parametrize(
    "reason",
    [
        SourceReason.AUTH,
        SourceReason.RATE_LIMIT,
        SourceReason.TIMEOUT,
        SourceReason.UPSTREAM,
        SourceReason.INVALID_RESPONSE,
    ],
)
def test_error_dengan_alasan_diterima(reason):
    result = SourceResult(source="abuseipdb", status=SourceStatus.ERROR, reason=reason)

    assert result.reason is reason


def test_kode_alasan_skipped_sama_dengan_string_yang_dipakai_collect_sources():
    # ip_checks.collect_sources masih memakai string ini sampai Tahap 2 menyambungkan adapter.
    assert SourceReason.ADAPTER_NOT_IMPLEMENTED == "ADAPTER_NOT_IMPLEMENTED"
    assert SourceReason.QUOTA_INTERNAL == "QUOTA_INTERNAL"
