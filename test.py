from greenscore import calculate_green_score
import json

data = {
    # compulsory to fill
    "building_type": "Institutional",  # Institutional or Commercial
    "operational_years": 1,   # >= 1

    # optional to fill
    "dry_waste_reduction_percent": 25,
    "wet_waste_composted_percent": 80,
    "potable_water_savings_percent": 35
}
print(json.dumps(calculate_green_score(data), indent=2))