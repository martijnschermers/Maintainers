import re


def format_license_plate(license_plate):
    value = re.sub(r"[\s-]", "", license_plate or "").upper()
    dutch_formats = (
        (r"^[A-Z]{2}\d{3}[A-Z]$", (2, 3, 1)),
        (r"^[A-Z]\d{3}[A-Z]{2}$", (1, 3, 2)),
        (r"^[A-Z]{3}\d{2}[A-Z]$", (3, 2, 1)),
        (r"^[A-Z]\d{2}[A-Z]{3}$", (1, 2, 3)),
        (r"^\d{2}[A-Z]{3}\d$", (2, 3, 1)),
        (r"^\d[A-Z]{3}\d{2}$", (1, 3, 2)),
    )
    for pattern, group_lengths in dutch_formats:
        if re.fullmatch(pattern, value):
            groups = []
            start = 0
            for length in group_lengths:
                groups.append(value[start : start + length])
                start += length
            return "-".join(groups)
    if len(value) == 6:
        return f"{value[:2]}-{value[2:4]}-{value[4:]}"
    return value
