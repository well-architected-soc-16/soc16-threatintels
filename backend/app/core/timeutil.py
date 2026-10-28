from datetime import UTC, datetime, timedelta, timezone

WIB = timezone(timedelta(hours=7))


def to_wib_iso(value: datetime) -> str:
    """ISO 8601 dengan offset +07:00. Datetime naive dianggap UTC."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(WIB).isoformat(timespec="seconds")


def now_wib_iso() -> str:
    return to_wib_iso(datetime.now(UTC))
