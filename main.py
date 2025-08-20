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

def extract_param_metadata(standard):
    """Extract all parameter metadata (label, description, input_type, units) from JSON."""
    params = {}
    for category in standard.get("categories", []):
        for credit in category.get("credits", []):
            calc = credit.get("calculation", {})
            ctype = calc.get("type")
            if ctype == "conditional_sum":
                for cond in calc.get("conditions", []):
                    p = cond.get("param")
                    if p:
                        params[p] = {
                            "label": cond.get("label", cond.get("name", p)),
                            "description": cond.get("description"),
                            "input_type": cond.get("input_type", "number"),
                            "units": cond.get("units")
                        }
            elif ctype == "either_or":
                for opt in calc.get("options", []):
                    for cond in opt.get("conditions", []):
                        p = cond.get("param")
                        if p:
                            params[p] = {
                                "label": cond.get("label", cond.get("name", p)),
                                "description": cond.get("description"),
                                "input_type": cond.get("input_type", "number"),
                                "units": cond.get("units")
                            }
            elif ctype == "composite_sum":
                for part in calc.get("parts", []):
                    p = part.get("param")
                    if p:
                        params[p] = {
                            "label": part.get("label", part.get("name", p)),
                            "description": part.get("description"),
                            "input_type": part.get("input_type", "number"),
                            "units": part.get("units")
                        }
            elif ctype == "single_condition":
                cond = calc.get("condition", {})
                p = cond.get("param")
                if p:
                    params[p] = {
                        "label": cond.get("label", cond.get("name", p)),
                        "description": cond.get("description"),
                        "input_type": cond.get("input_type", "number"),
                        "units": cond.get("units")
                    }
                add = calc.get("additional_requirements", {})
                p2 = add.get("param")
                if p2:
                    params[p2] = {
                        "label": add.get("label", add.get("name", p2)),
                        "description": add.get("description"),
                        "input_type": add.get("input_type", "number"),
                        "units": add.get("units")
                    }
            elif ctype == "range_based":
                p = calc.get("param")
                if p:
                    params[p] = {
                        "label": calc.get("label", calc.get("name", p)),
                        "description": calc.get("description"),
                        "input_type": calc.get("input_type", "number"),
                        "units": calc.get("units")
                    }
    return params

def build_question(param_metadata):
    """Build a question string from parameter metadata."""
    label = param_metadata["label"]
    description = param_metadata.get("description")
    if description:
        return f"{label} - {description}"
    return label

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

    return (len(failed_reasons) == 0, failed_reasons)

def main():
    # Load standard
    with open("advant_standard.json") as f:
        standard = json.load(f)

    calc = GreenScoreCalculator(standard)
    param_metadata = extract_param_metadata(standard)

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

    eligibility_data = {
        "building_type": building_type,
        "operational_years": operational_years
    }

    # Full eligibility check
    eligible, failed_reasons = check_eligibility_full(calc, eligibility_data)
    if not eligible:
        print("\n=== Evaluation Result ===")
        print(json.dumps({"eligible": False, "reasons": failed_reasons}, indent=2))
        return

    # Ask all parameters dynamically from JSON metadata
    params = {}
    
    # Collect all parameters dynamically from JSON metadata
    # Sort param keys to maintain consistent order (param1, param2, etc.)
    param_keys = sorted([k for k in param_metadata.keys() if k.startswith('param')], 
                       key=lambda x: int(x.replace('param', '')))
    
    for param_key in param_keys:
        meta = param_metadata[param_key]
        question = build_question(meta)
        
        if meta["input_type"] == "boolean":
            params[param_key] = ask_yes_no(question, optional=True)
        else:  # number
            params[param_key] = ask_numeric(question, optional=True)

    building_data = {
        **eligibility_data,
        **params
    }

    # Evaluate
    result = calc.evaluate(building_data)

    # Collect met and unmet criteria per param for all credits
    met_criteria = []
    unmet_criteria = []
    
    def analyze_credit(credit, building_data, result):
        """Analyze a single credit and return met/unmet entries."""
        calc = credit.get("calculation", {})
        calc_type = calc.get("type")
        credit_score = result.get("credit_scores", {}).get(credit["sub_id"], 0)
        
        if calc_type == "conditional_sum":
            for cond in calc["conditions"]:
                val = building_data.get(cond["param"])
                met = val is not None and val >= cond["threshold"]
                entry = {
                    "credit_id": credit["sub_id"],
                    "param": cond["param"],
                    "param_name": cond.get("label", cond.get("name", cond["param"])),
                    "points": cond["points"],
                    "met": met,
                    "requirement": f">= {cond['threshold']} {cond.get('units', '')}".strip()
                }
                if met:
                    met_criteria.append(entry)
                else:
                    unmet_criteria.append(entry)
                    
        elif calc_type == "either_or":
            for opt in calc.get("options", []):
                group_points = opt.get("points", 1)
                group_label = opt.get("group", "")
                conditions = opt.get("conditions", [])
                
                # Check if any condition in the group is met
                group_met = False
                for condition in conditions:
                    val = building_data.get(condition["param"])
                    if "threshold" in condition:
                        if val is not None and val >= condition["threshold"]:
                            group_met = True
                            break
                    elif "value" in condition:
                        if val == condition["value"]:
                            group_met = True
                            break
                
                if group_met:
                    met_criteria.append({
                        "credit_id": credit["sub_id"],
                        "credit_name": f"{credit['name']} - {group_label}",
                        "points": group_points,
                        "max_points": group_points
                    })
                else:
                    # Build readable requirement text
                    parts = []
                    for c in conditions:
                        label = c.get("label", c.get("name", c["param"]))
                        if "threshold" in c:
                            parts.append(f"{label} >= {c['threshold']} {c.get('units', '')}".strip())
                        elif "value" in c:
                            parts.append(f"{label} = {c['value']}")
                    
                    requirement_text = f"Meet at least one: {' OR '.join(parts)}"
                    unmet_criteria.append({
                        "credit_id": credit["sub_id"],
                        "credit_name": f"{credit['name']} - {group_label}",
                        "requirement": requirement_text,
                        "max_points": group_points
                    })
                    
        elif calc_type == "composite_sum":
            total_earned = 0
            for part in calc.get("parts", []):
                val = building_data.get(part["param"])
                part_points = 0
                part_met = False
                
                for r in part["ranges"]:
                    min_val = r.get("min")
                    max_val = r.get("max")
                    
                    # Check if value falls within range
                    min_ok = min_val is None or (val is not None and val >= min_val)
                    max_ok = max_val is None or (val is not None and val <= max_val)
                    
                    if min_ok and max_ok:
                        part_points = r["points"]
                        part_met = True
                        break
                
                total_earned += part_points
                label = part.get("label", part.get("name", part["param"]))
                
                if part_met:
                    met_criteria.append({
                        "credit_id": credit["sub_id"],
                        "param": part["param"],
                        "param_name": label,
                        "points": part_points,
                        "met": True
                    })
                else:
                    # Show range requirements
                    ranges_text = []
                    for r in part["ranges"]:
                        min_val = r.get("min", 0)
                        max_val = r.get("max", "∞")
                        ranges_text.append(f"{min_val}-{max_val}: {r['points']} pts")
                    
                    unmet_criteria.append({
                        "credit_id": credit["sub_id"],
                        "param": part["param"],
                        "param_name": label,
                        "points": 0,
                        "met": False,
                        "requirement": f"Ranges: {', '.join(ranges_text)}"
                    })
                    
        elif calc_type == "single_condition":
            cond = calc.get("condition", {})
            add_req = calc.get("additional_requirements", {})
            
            val = building_data.get(cond["param"])
            add_val = building_data.get(add_req.get("param")) if add_req.get("param") else None
            
            main_met = val is not None and val >= cond["threshold"]
            add_met = add_val is None or add_val >= add_req.get("min_required", 0)
            
            if main_met and add_met:
                met_criteria.append({
                    "credit_id": credit["sub_id"],
                    "credit_name": credit["name"],
                    "points": cond["points"],
                    "max_points": credit["max_points"]
                })
            else:
                requirements = []
                main_label = cond.get("label", cond.get("name", cond["param"]))
                requirements.append(f"{main_label} >= {cond['threshold']} {cond.get('units', '')}".strip())
                
                if add_req.get("param"):
                    add_label = add_req.get("label", add_req.get("name", add_req["param"]))
                    requirements.append(f"{add_label} >= {add_req['min_required']} {add_req.get('units', '')}".strip())
                
                unmet_criteria.append({
                    "credit_id": credit["sub_id"],
                    "credit_name": credit["name"],
                    "requirement": f"Must meet ALL: {' AND '.join(requirements)}",
                    "max_points": credit["max_points"]
                })
                
        elif calc_type == "range_based":
            val = building_data.get(calc["param"])
            param_label = calc.get("label", calc.get("name", calc["param"]))
            met = False
            points = 0
            
            for r in calc["ranges"]:
                min_val = r.get("min")
                max_val = r.get("max")
                
                # Check if value falls within range
                min_ok = min_val is None or (val is not None and val >= min_val)
                max_ok = max_val is None or (val is not None and val <= max_val)
                
                if min_ok and max_ok:
                    met = True
                    points = r["points"]
                    break
            
            entry = {
                "credit_id": credit["sub_id"],
                "param": calc["param"],
                "param_name": param_label,
                "points": points,
                "met": met
            }
            
            if met:
                met_criteria.append(entry)
            else:
                # Show range requirements
                ranges_text = []
                for r in calc["ranges"]:
                    min_val = r.get("min", 0)
                    max_val = r.get("max", "∞")
                    ranges_text.append(f"{min_val}-{max_val}: {r['points']} pts")
                
                entry["requirement"] = f"Ranges: {', '.join(ranges_text)}"
                unmet_criteria.append(entry)
    
    for category in standard["categories"]:
        for credit in category["credits"]:
            analyze_credit(credit, building_data, result)

    print("\n=== Evaluation Result ===")
    print(f"Eligible: {result['eligible']}")
    print(f"Total Green Score: {result['total_score']}")
    print(f"Certification Level: {result.get('certification_level', 'Not certified yet')}")
    
    print("\nCategory Scores:")
    for category in standard["categories"]:
        category_id = category["id"]
        category_name = category["name"]
        category_score = result.get('category_scores', {}).get(category_id, 0)
        category_max = category["max_points"]
        print(f" - {category_id} ({category_name}): {category_score}/{category_max} points")

    print("\nUnmet Criteria:")
    if unmet_criteria:
        for c in unmet_criteria:
            if c.get("param"):
                req_text = f" ({c.get('requirement', '')})" if c.get('requirement') else ""
                print(f" - {c['credit_id']} {c['param_name']}: Not met{req_text}, Max Points: {c.get('points', 0)}")
            else:
                print(f" - {c['credit_id']} ({c.get('credit_name', '')}):\n    {c.get('requirement', 'No requirement info')}\n    Max Points: {c.get('max_points', 0)}")
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
