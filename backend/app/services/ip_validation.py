"""Validasi input IP v1: satu IPv4 publik saja.

Fungsi di sini murni (tanpa I/O). Input yang ditolak tidak boleh sampai ke
adapter sumber eksternal; pemanggil wajib memeriksa hasilnya dulu.
"""

import enum
import ipaddress
from dataclasses import dataclass

# Jauh di atas panjang IPv6 terpanjang (45); mencegah input raksasa diproses.
MAX_INPUT_LENGTH = 64

_THIS_NETWORK = ipaddress.ip_network("0.0.0.0/8")
_DOCUMENTATION_NETWORKS = (
    ipaddress.ip_network("192.0.2.0/24"),  # TEST-NET-1
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),  # TEST-NET-3
)


class ReasonCode(enum.StrEnum):
    INVALID_FORMAT = "INVALID_FORMAT"
    IPV6_NOT_SUPPORTED = "IPV6_NOT_SUPPORTED"
    LOOPBACK = "LOOPBACK"
    LINK_LOCAL = "LINK_LOCAL"
    MULTICAST = "MULTICAST"
    UNSPECIFIED = "UNSPECIFIED"
    DOCUMENTATION = "DOCUMENTATION"
    RESERVED = "RESERVED"
    PRIVATE = "PRIVATE"
    NOT_GLOBAL = "NOT_GLOBAL"


MESSAGES: dict[ReasonCode, str] = {
    ReasonCode.INVALID_FORMAT: "Format bukan alamat IPv4 yang valid",
    ReasonCode.IPV6_NOT_SUPPORTED: "IPv6 belum didukung",
    ReasonCode.LOOPBACK: "Alamat loopback tidak diperiksa",
    ReasonCode.LINK_LOCAL: "Alamat link-local tidak diperiksa",
    ReasonCode.MULTICAST: "Alamat multicast tidak diperiksa",
    ReasonCode.UNSPECIFIED: "Alamat unspecified tidak diperiksa",
    ReasonCode.DOCUMENTATION: "Alamat dokumentasi tidak diperiksa",
    ReasonCode.RESERVED: "Alamat reserved tidak diperiksa",
    ReasonCode.PRIVATE: "Alamat privat/internal tidak diperiksa",
    ReasonCode.NOT_GLOBAL: "Alamat bukan IP publik (non-global)",
}


@dataclass(frozen=True)
class IpValidation:
    valid: bool
    # IP dalam bentuk kanonik; hanya terisi jika valid.
    ip: str | None = None
    reason_code: ReasonCode | None = None

    @property
    def message(self) -> str | None:
        return MESSAGES[self.reason_code] if self.reason_code else None


def _reject(reason: ReasonCode) -> IpValidation:
    return IpValidation(valid=False, reason_code=reason)


def validate_ip(raw: str) -> IpValidation:
    text = raw.strip()
    if not text or len(text) > MAX_INPUT_LENGTH:
        return _reject(ReasonCode.INVALID_FORMAT)

    try:
        ip = ipaddress.ip_address(text)
    except ValueError:
        return _reject(ReasonCode.INVALID_FORMAT)

    if isinstance(ip, ipaddress.IPv6Address):
        return _reject(ReasonCode.IPV6_NOT_SUPPORTED)

    # Urutan penting: is_private tumpang-tindih dengan loopback, link-local,
    # dokumentasi, dan reserved, jadi kategori yang lebih spesifik dicek lebih dulu.
    if ip.is_loopback:
        return _reject(ReasonCode.LOOPBACK)
    if ip.is_link_local:
        return _reject(ReasonCode.LINK_LOCAL)
    if ip.is_multicast:
        return _reject(ReasonCode.MULTICAST)
    if ip.is_unspecified:
        return _reject(ReasonCode.UNSPECIFIED)
    if any(ip in net for net in _DOCUMENTATION_NETWORKS):
        return _reject(ReasonCode.DOCUMENTATION)
    if ip.is_reserved or ip in _THIS_NETWORK:
        return _reject(ReasonCode.RESERVED)
    if ip.is_private:
        return _reject(ReasonCode.PRIVATE)
    if not ip.is_global:
        # Mis. 100.64.0.0/10 (shared address space): bukan privat, tapi tidak global.
        return _reject(ReasonCode.NOT_GLOBAL)

    return IpValidation(valid=True, ip=str(ip))
