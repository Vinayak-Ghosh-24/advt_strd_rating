import json
from greenscore import GreenScoreCalculator

def ask_numeric(prompt, optional=False):
    while True:
        ans = input(prompt + (": " if not optional else " (Press Enter to skip): ")).strip()
        if ans == "" and optional:
            return None
        try:
            return float(ans)
        except ValueError:
            print("❌ Please enter a valid number.")

def ask_yes_no(prompt, optional=False):
    while True:
        ans = input(prompt + (": " if not optional else " (yes/no, Enter to skip): ")).strip().lower()
        if ans == "" and optional:
            return None
        if ans in ["yes", "y"]:
            return True
        elif ans in ["no", "n"]:
            return False
        else:
            print("❌ Please type yes or no, or press Enter to skip.")

def check_eligibility_full(calc, data):
    """Returns eligibility status and all reasons for failure"""
    failed_reasons = []
    ec = calc.standard["eligibility_criteria"]

    # Check building type
    if data["building_type"] not in ec["building_type"]:
        failed_reasons.append(f"Building type must be one of {ec['building_type']}")

    # Check operational years
    min_years = ec["operational_years"]["$gte"]
    if data["operational_years"] < min_years:
        failed_reasons.append(f"Building must be operational for at least {min_years} years")

    # Check floor area
    min_area = ec["floor_area_m2"]["$gt"]
    if data["floor_area_m2"] <= min_area:
        failed_reasons.append(f"Building floor area must be greater than {min_area} m²")

    return (len(failed_reasons) == 0, failed_reasons)

def main():
    # Load standard
    with open("advant_standard.json") as f:
        standard = json.load(f)

    calc = GreenScoreCalculator(standard)

    print("=== Advant Green Building Evaluation ===")

    # Building type selection with numbers
    print("Select building type:")
    for idx, btype in enumerate(standard['eligibility_criteria']['building_type'], start=1):
        print(f"{idx}. {btype}")
    while True:
        choice = input("Enter 1 or 2: ").strip()
        if choice in ["1", "2"]:
            building_type = standard['eligibility_criteria']['building_type'][int(choice) - 1]
            break
        else:
            print("❌ Please enter a valid choice (1 or 2)")

    operational_years = ask_numeric("How many years has the building been operational?")
    floor_area_m2 = ask_numeric("Enter floor area in square meters")

    eligibility_data = {
        "building_type": building_type,
        "operational_years": operational_years,
        "floor_area_m2": floor_area_m2
    }

    # Full eligibility check
    eligible, failed_reasons = check_eligibility_full(calc, eligibility_data)
    if not eligible:
        print("\n=== Evaluation Result ===")
        print(json.dumps({"eligible": False, "reasons": failed_reasons}, indent=2))
        return

    # Ask non-eligibility params (skippable)
    # Use param1, param2, param3 for SF1
    param1 = ask_numeric("Dry waste reduction percentage compared to last year", optional=True)
    param2 = ask_numeric("Dry waste recycled percentage", optional=True)
    param3 = ask_numeric("Wet waste composted percentage", optional=True)

    param4 = ask_numeric("Eco-labelled product cost percentage during retrofitting", optional=True)
    param5 = ask_numeric("Number of certified green products used", optional=True)
    param6 = ask_yes_no("Does the building have a sustainable procurement policy?", optional=True)

    param7 = ask_numeric("Potable water savings percentage over baseline", optional=True)

    building_data = {
        **eligibility_data,
        "param1": param1,
        "param2": param2,
        "param3": param3,
        "param4": param4,
        "param5": param5,
        "param6": param6,
        "param7": param7
    }

    # Evaluate
    result = calc.evaluate(building_data)

    # Collect met and unmet criteria per param for all credits
    met_criteria = []
    unmet_criteria = []
    for category in standard["categories"]:
        for credit in category["credits"]:
            calc = credit.get("calculation", {})
            if credit["id"] == "SF1" and calc.get("type") == "conditional_sum":
                for cond in calc["conditions"]:
                    val = building_data.get(cond["param"])
                    met = val is not None and val >= cond["threshold"]
                    entry = {
                        "credit_id": credit["id"],
                        "param": cond["param"],
                        "param_name": cond["name"],
                        "points": cond["points"],
                        "met": met
                    }
                    if met:
                        met_criteria.append(entry)
                    else:
                        unmet_criteria.append(entry)
            elif credit["id"] == "SF2" and calc.get("type") == "either_or":
                for opt in calc.get("options", []):
                    group_points = opt.get("points", 1)
                    group_label = opt.get("group", "")
                    conditions = opt.get("conditions", [])

                    # Determine if any condition in the group is met
                    group_met = False
                    satisfied_condition = None
                    for condition in conditions:
                        val = building_data.get(condition["param"])
                        if "threshold" in condition:
                            if val is not None and val >= condition["threshold"]:
                                group_met = True
                                satisfied_condition = condition
                                break
                        elif "value" in condition:
                            if val == condition["value"]:
                                group_met = True
                                satisfied_condition = condition
                                break

                    if group_met:
                        # Record a single met entry at the group level
                        met_criteria.append({
                            "credit_id": credit["id"],
                            "credit_name": f"{credit['name']} - {group_label}",
                            "points": group_points,
                            "max_points": group_points
                        })
                    else:
                        # If no condition met, record a single unmet entry describing the either/or requirement
                        if len(conditions) > 1:
                            parts = []
                            for c in conditions:
                                cname = c.get("name", c["param"])
                                if "threshold" in c:
                                    parts.append(f"{c['param']} ({cname}) >= {c['threshold']}")
                                elif "value" in c:
                                    parts.append(f"{c['param']} ({cname}) == {json.dumps(c['value'])}")
                                else:
                                    parts.append(f"{c['param']} ({cname})")
                            requirement_text = f"Meet at least one: " + "; ".join(parts) + f" for {group_points} point(s)"
                            unmet_criteria.append({
                                "credit_id": credit["id"],
                                "credit_name": f"{credit['name']} - {group_label}",
                                "requirement": requirement_text,
                                "max_points": group_points
                            })
                        elif len(conditions) == 1:
                            # Single-condition group: show unmet at the param level
                            c = conditions[0]
                            unmet_criteria.append({
                                "credit_id": credit["id"],
                                "param": c["param"],
                                "param_name": c.get("name", c["param"]),
                                "points": group_points,
                                "met": False
                            })
            elif credit["id"] == "WC1" and calc.get("type") == "range_based":
                val = building_data.get(calc["param"])
                param_name = calc.get("name", calc["param"])
                met = False
                points = 0
                for r in calc["ranges"]:
                    if r["min"] is not None and val is not None and val >= r["min"]:
                        if r["max"] is None or val <= r["max"]:
                            met = True
                            points = r["points"]
                            break
                entry = {
                    "credit_id": credit["id"],
                    "param": calc["param"],
                    "param_name": param_name,
                    "points": points,
                    "met": met
                }
                if met:
                    met_criteria.append(entry)
                else:
                    unmet_criteria.append(entry)
            else:
                score = result.get("credit_scores", {}).get(credit["id"], 0)
                if score and score > 0:
                    met_criteria.append({
                        "credit_id": credit["id"],
                        "credit_name": credit["name"],
                        "points": score,
                        "max_points": credit["max_points"]
                    })
                else:
                    unmet_criteria.append({
                        "credit_id": credit["id"],
                        "credit_name": credit["name"],
                        "max_points": credit["max_points"],
                        "requirement": credit.get("calculation", {})
                    })

    print("\n=== Evaluation Result ===")
    print(f"Eligible: {result['eligible']}")
    print(f"Total Green Score: {result['total_score']}")
    print(f"Certification Level: {result.get('certification_level', 'Not certified yet')}")

    print("\nUnmet Criteria:")
    if unmet_criteria:
        for c in unmet_criteria:
            if c.get("param"):
                print(f" - {c['credit_id']} {c['param']} ({c['param_name']}): Not met, Points: {c['points']}")
            else:
                print(f" - {c['credit_id']} ({c.get('credit_name','')}):\n    Requirement: {json.dumps(c.get('requirement',''))}\n    Max Points: {c.get('max_points','')}")
    else:
        print("✅ All criteria met")

    print("\nMet Criteria:")
    if met_criteria:
        for c in met_criteria:
            if c.get("param"):
                print(f" - {c['credit_id']} {c['param']} ({c['param_name']}): Met, Points: {c['points']}")
            else:
                print(f" - {c['credit_id']} ({c.get('credit_name','')}): {c.get('points','')} / {c.get('max_points','')} points")
    else:
        print("No criteria met.")

if __name__ == "__main__":
    main()
