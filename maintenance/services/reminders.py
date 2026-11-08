from collections import defaultdict
from datetime import date, timedelta


def build_maintenance_reminders(entries, current_odometer, today=None):
    """Estimate the next maintenance moment from the latest two entries per category."""
    today = today or date.today()
    grouped_entries = defaultdict(list)
    for entry in entries:
        grouped_entries[entry.category].append(entry)

    reminders = []
    for category_entries in grouped_entries.values():
        if len(category_entries) < 2:
            continue
        previous, latest = sorted(category_entries, key=lambda entry: (entry.performed_on, entry.odometer_km))[-2:]
        date_interval = max((latest.performed_on - previous.performed_on).days, 1)
        odometer_interval = max(latest.odometer_km - previous.odometer_km, 1)
        due_date = latest.performed_on + timedelta(days=date_interval)
        due_odometer = latest.odometer_km + odometer_interval
        is_due = today >= due_date or current_odometer >= due_odometer
        reminders.append(
            {
                "category": latest.get_category_display(),
                "due_date": due_date,
                "due_odometer": due_odometer,
                "status": "due" if is_due else "upcoming",
            }
        )

    return sorted(reminders, key=lambda reminder: (reminder["status"] != "due", reminder["due_date"]))
