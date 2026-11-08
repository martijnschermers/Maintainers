def export_user_data(user):
    return {
        "user": {"username": user.username, "email": user.email, "date_joined": user.date_joined.isoformat()},
        "vehicles": [
            {
                "make": vehicle.make,
                "model": vehicle.model,
                "license_plate": vehicle.license_plate,
                "vin": vehicle.vin,
                "entries": [
                    {
                        "date": str(entry.performed_on),
                        "odometer_km": entry.odometer_km,
                        "category": entry.category,
                        "description": entry.description,
                        "cost": f"{entry.total_cost:.2f}",
                        "currency": entry.currency,
                    }
                    for entry in vehicle.maintenance_entries.all()
                ],
            }
            for vehicle in user.vehicles.all()
        ],
    }
