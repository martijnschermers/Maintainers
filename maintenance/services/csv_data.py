import csv
import io


def export_vehicle_csv(vehicle):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["datum", "kilometerstand_km", "categorie", "omschrijving", "uitgevoerd_door", "kosten", "valuta", "notities"]
    )
    for entry in vehicle.maintenance_entries.all():
        writer.writerow([
            entry.performed_on,
            entry.odometer_km,
            entry.get_category_display(),
            entry.description,
            entry.get_performed_by_display(),
            f"{entry.total_cost:.2f}",
            entry.currency,
            entry.notes,
        ])
    return output.getvalue()
