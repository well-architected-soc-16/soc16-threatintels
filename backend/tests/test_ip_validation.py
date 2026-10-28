import pytest

from app.services.ip_validation import MAX_INPUT_LENGTH, ReasonCode, validate_ip


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("8.8.8.8", "8.8.8.8"),
        ("1.1.1.1", "1.1.1.1"),
        ("  8.8.8.8  ", "8.8.8.8"),
        ("8.8.8.8\n", "8.8.8.8"),
    ],
)
def test_ip_publik_valid(raw, expected):
    result = validate_ip(raw)

    assert result.valid is True
    assert result.ip == expected
    assert result.reason_code is None
    assert result.message is None


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        ("10.0.0.5", ReasonCode.PRIVATE),
        ("172.16.0.1", ReasonCode.PRIVATE),
        ("192.168.1.1", ReasonCode.PRIVATE),
        ("127.0.0.1", ReasonCode.LOOPBACK),
        ("169.254.1.1", ReasonCode.LINK_LOCAL),
        ("224.0.0.1", ReasonCode.MULTICAST),
        ("0.0.0.0", ReasonCode.UNSPECIFIED),
        ("192.0.2.1", ReasonCode.DOCUMENTATION),
        ("198.51.100.7", ReasonCode.DOCUMENTATION),
        ("203.0.113.9", ReasonCode.DOCUMENTATION),
        ("240.0.0.1", ReasonCode.RESERVED),
        ("255.255.255.255", ReasonCode.RESERVED),
        ("0.1.2.3", ReasonCode.RESERVED),
        ("100.64.0.1", ReasonCode.NOT_GLOBAL),
    ],
)
def test_ipv4_non_publik_ditolak_dengan_reason_tepat(raw, reason):
    result = validate_ip(raw)

    assert result.valid is False
    assert result.ip is None
    assert result.reason_code == reason
    assert result.message


@pytest.mark.parametrize(
    "raw",
    ["::1", "2001:4860:4860::8888", "fe80::1", "::ffff:10.0.0.1", "fe80::1%eth0"],
)
def test_ipv6_ditolak_belum_didukung(raw):
    assert validate_ip(raw).reason_code == ReasonCode.IPV6_NOT_SUPPORTED


@pytest.mark.parametrize(
    "raw",
    [
        "abc",
        "",
        "   ",
        "8.8.8",
        "8.8.8.8.8",
        "256.1.1.1",
        "08.8.8.8",
        "8.8.8.8:80",
        "8.8.8.0/24",
        "134744072",
        "8.8.8.8 1.1.1.1",
        "８.８.８.８",
        "a" * (MAX_INPUT_LENGTH + 1),
    ],
)
def test_format_tidak_valid_ditolak(raw):
    assert validate_ip(raw).reason_code == ReasonCode.INVALID_FORMAT
