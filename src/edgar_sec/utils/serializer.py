from datetime import date


def filing_serializer(obj: object) -> str:
    """Serialize objects with fields in type EntityFilings of EdgarTools.

    Args:
        obj: The object to serialize.

    Returns:
        A string representation of the date if obj is a date, else raises TypeError.
    """
    if isinstance(obj, date):
        return obj.isoformat()  # Convert date to ISO 8601 format
    return str(obj)
