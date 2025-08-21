import json

class GreenScoreCalculator:
    def __init__(self, standard_json):
        if isinstance(standard_json, str):
            standard_json = json.loads(standard_json)
        self.standard = standard_json

    def check_eligibility(self, building_data):
        criteria = self.standard["eligibility_criteria"]
        
        # Check building type
        if building_data.get("building_type") not in criteria["building_type"]:
            return False, "Building type not eligible"
        
        # Check operational years
        if building_data.get("operational_years", 0) < criteria["operational_years"]["$gte"]:
            return False, "Building has not been operational long enough"
        
        return True, "Eligible"

    def calculate_credit_points(self, credit, building_data):
        calc_type = credit["calculation"]["type"]
        max_points = credit["max_points"]

        def safe_num(val):
            return 0 if val is None else val

        if calc_type == "conditional_sum":
            total = 0
            condition_results = []
            for cond in credit["calculation"]["conditions"]:
                val = safe_num(building_data.get(cond["param"]))
                if val >= cond["threshold"]:
                    total += cond["points"]
                    condition_results.append({"condition": cond["name"], "result": True, "points": cond["points"]})
                else:
                    condition_results.append({"condition": cond["name"], "result": False, "points": 0})
            return min(total, max_points), condition_results

        elif calc_type == "either_or":
            points = 0
            condition_results = []
            for option in credit["calculation"]["options"]:
                group_points = 0
                group_max = option.get("points", 1)  # Default to 1 point per group if not specified
                
                # Check all conditions in this group
                for condition in option.get("conditions", []):
                    val = building_data.get(condition["param"])
                    
                    # Check threshold condition
                    if "threshold" in condition and val is not None and val >= condition["threshold"]:
                        group_points = group_max
                        condition_results.append({"condition": condition["name"], "result": True, "points": group_max})
                        break  # Only need one condition in the group to be true
                        
                    # Check value condition
                    if "value" in condition and building_data.get(condition["param"]) == condition["value"]:
                        group_points = group_max
                        condition_results.append({"condition": condition["name"], "result": True, "points": group_max})
                        break  # Only need one condition in the group to be true
                
                points += group_points
                if group_points == 0:
                    for condition in option.get("conditions", []):
                        condition_results.append({"condition": condition["name"], "result": False, "points": 0})
            
            return min(points, max_points), condition_results

        elif calc_type == "range_based":
            val = safe_num(building_data.get(credit["calculation"]["param"]))
            for r in credit["calculation"]["ranges"]:
                min_val = r.get("min")
                max_val = r.get("max")
                
                # Check if value falls within range
                min_ok = min_val is None or val >= min_val
                max_ok = max_val is None or val <= max_val
                
                if min_ok and max_ok:
                    return r["points"], [{"condition": credit["calculation"]["name"], "result": True, "points": r["points"]}]
            return 0, [{"condition": credit["calculation"]["name"], "result": False, "points": 0}]
        
        elif calc_type == "composite_sum":
            score = 0
            condition_results = []
            for part in credit["calculation"]["parts"]:
                val = safe_num(building_data.get(part["param"]))
                for r in part["ranges"]:
                    min_val = r.get("min")
                    max_val = r.get("max")
                    
                    # Check if value falls within range
                    min_ok = min_val is None or val >= min_val
                    max_ok = max_val is None or val <= max_val
                    
                    if min_ok and max_ok:
                        score += r["points"]
                        condition_results.append({"condition": part["name"], "result": True, "points": r["points"]})
                        break
            return min(score, max_points), condition_results

        elif calc_type == "single_condition":
            cond = credit["calculation"]["condition"]
            min_req = credit["calculation"].get("additional_requirements", {})
            val = safe_num(building_data.get(cond["param"]))
            min_val = safe_num(building_data.get(min_req.get("param")))
            if val >= cond["threshold"] and min_val >= min_req.get("min_required", 0):
                return cond["points"], [{"condition": cond["name"], "result": True, "points": cond["points"]}]
            return 0, [{"condition": cond["name"], "result": False, "points": 0}]

        return 0, []

    def calculate_total_score(self, building_data):
        total_score = 0
        category_scores = {}
        credit_scores = {}

        for category in self.standard["categories"]:
            cat_score = 0
            for credit in category["credits"]:
                points, condition_results = self.calculate_credit_points(credit, building_data)
                credit_scores[credit["sub_id"]] = {"points": points, "conditions": condition_results}
                cat_score += points
            cat_score = min(cat_score, category["max_points"])
            category_scores[category["id"]] = cat_score
            total_score += cat_score

        return total_score, category_scores, credit_scores

    def get_certification_level(self, total_score):
        for level in self.standard["scoring_info"]["certification_levels"]:
            if level["min_points"] <= total_score <= level["max_points"]:
                return level["name"]
        return "No Certification"


    def evaluate_enhanced(self, building_data):
        eligible, reason = self.check_eligibility(building_data)
        if not eligible:
            return {"eligible": False, "reason": reason}

        total_score, category_scores, credit_scores = self.calculate_total_score(building_data)
        level = self.get_certification_level(total_score)

        return {
            "eligible": True,
            "green_score": total_score,
            "category_scores": category_scores,
            "credit_scores": credit_scores,
            "certification_level": level
        }





def calculate_green_score(data):
    """
    Simplified function that accepts standardized variable names from JSON schema.
    
    Args:
        data (dict): Dictionary with standardized variable names as keys and their values
        Expected keys include:
        - dry_waste_reduction_percent
        - dry_waste_recycled_percent  
        - wet_waste_composted_percent
        - eco_labelled_product_cost_percent
        - certified_green_products_count
        - sustainable_procurement_policy
        - roof_uhi_coverage_percent
        - non_roof_uhi_coverage_percent
        - organic_fertilizer_coverage_percent
        - landscape_area_percent
        - public_transport_compliant
        - shuttle_service_coverage_percent
        - potable_water_savings_percent
        - gwp_refrigerants_fire_suppression
        
    Returns:
        dict: Evaluation result with total_score, certification_level, category_scores, credit_details
    """
    try:
        # Load the standard JSON
        with open("advant_standard.json", "r") as f:
            standard = json.load(f)
        
        # Create calculator instance
        calculator = GreenScoreCalculator(standard)
        
        # Convert standardized names to param format expected by calculator
        param_mapping = {
            "dry_waste_reduction_percent": "param1",
            "dry_waste_recycled_percent": "param2", 
            "wet_waste_composted_percent": "param3",
            "eco_labelled_product_cost_percent": "param4",
            "certified_green_products_count": "param5",
            "sustainable_procurement_policy": "param6",
            "roof_uhi_coverage_percent": "param7",
            "non_roof_uhi_coverage_percent": "param8",
            "organic_fertilizer_coverage_percent": "param9",
            "landscape_area_percent": "param10",
            "public_transport_compliant": "param11",
            "shuttle_service_coverage_percent": "param12",
            "potable_water_savings_percent": "param13",
            "gwp_refrigerants_fire_suppression": "param14"
        }
        
        # Convert data to param format
        building_data = {
            "building_type": "Commercial",  # Default
            "operational_years": 2,         # Default
        }
        
        for std_name, value in data.items():
            if std_name in param_mapping:
                building_data[param_mapping[std_name]] = value
            elif std_name in ["building_type", "operational_years"]:
                building_data[std_name] = value
        
        # Use the enhanced evaluation method
        result = calculator.evaluate_enhanced(building_data)
        
        # Return result with renamed field for consistency
        if result.get("eligible", True):
            result["credit_details"] = result.pop("credit_scores")
        
        return result
        
    except Exception as e:
        return {"error": str(e)}




# -------------------------
# Name-based API extensions
# -------------------------

def _load_standard():
    with open("advant_standard.json", "r") as f:
        return json.load(f)


def _iter_questions(standard):
    """
    Yields tuples of (category_id, credit_sub_id, question_dict) for every input in the standard,
    including nested parts/options and additional requirements where applicable.
    """
    for category in standard.get("categories", []):
        cat_id = category.get("id")
        for credit in category.get("credits", []):
            sub_id = credit.get("sub_id")
            calc = credit.get("calculation", {})
            ctype = calc.get("type")

            if ctype == "conditional_sum":
                for cond in calc.get("conditions", []):
                    yield cat_id, sub_id, cond

            elif ctype == "either_or":
                for option in calc.get("options", []):
                    for condition in option.get("conditions", []):
                        yield cat_id, sub_id, condition

            elif ctype == "range_based":
                yield cat_id, sub_id, calc

            elif ctype == "composite_sum":
                for part in calc.get("parts", []):
                    yield cat_id, sub_id, part

            elif ctype == "single_condition":
                yield cat_id, sub_id, calc.get("condition", {})
                add_req = calc.get("additional_requirements")
                if add_req:
                    # Expose as a separate question to the agent
                    yield cat_id, sub_id, add_req


def _build_name_param_maps(standard):
    """
    Builds and returns two dicts:
    - name_to_param: {name: param}
    - name_to_input_type: {name: input_type}
    """
    name_to_param = {}
    name_to_input_type = {}
    for _, _, q in _iter_questions(standard):
        name = q.get("name")
        param = q.get("param")
        if name and param:
            name_to_param[name] = param
            if q.get("input_type"):
                name_to_input_type[name] = q.get("input_type")
    return name_to_param, name_to_input_type


def get_input_schema():
    """Return a structured schema of inputs derived from advant_standard.json for an agent to ask.

    Includes eligibility prompts and all credit inputs with labels, descriptions, prompts,
    validation ranges/thresholds, units, and grouping metadata.
    """
    standard = _load_standard()

    schema = {
        "version": standard.get("version"),
        "standard_name": standard.get("name"),
        "eligibility": {
            "building_type": {
                "name": "building_type",
                "label": "Building Type",
                "description": "Type of the building",
                "input_type": "enum",
                "options": standard.get("eligibility_criteria", {}).get("building_type", []),
                "required": True,
            },
            "operational_years": {
                "name": "operational_years",
                "label": "Operational years",
                "description": "Number of years the building has been operational",
                "input_type": "number",
                "constraints": {
                    "$gte": standard.get("eligibility_criteria", {}).get("operational_years", {}).get("$gte")
                },
                "required": True,
            },
        },
        "questions": [],
    }

    for cat_id, sub_id, q in _iter_questions(standard):
        question = {
            "name": q.get("name"),
            "label": q.get("label"),
            "description": q.get("description"),
            "prompt": q.get("prompt-description"),
            "input_type": q.get("input_type", "number"),
            "units": q.get("units"),
            "category_id": cat_id,
            "credit_sub_id": sub_id,
        }

        # Add validation hints
        if "threshold" in q:
            question["threshold"] = q.get("threshold")
        if "ranges" in q:
            question["ranges"] = q.get("ranges")
        if "min_required" in q:
            question["min_required"] = q.get("min_required")

        schema["questions"].append(question)

    return schema


def evaluate_named(answers_by_name):
    """
    Evaluate using human-readable variable names from the JSON (e.g., 'dry_waste_reduction_percent').

    - Skipped numeric inputs default to 0
    - Skipped boolean inputs default to False
    - Backwards-compatible defaults for eligibility if not provided: building_type="Commercial", operational_years=2
    """
    try:
        standard = _load_standard()
        calculator = GreenScoreCalculator(standard)

        name_to_param, name_to_input_type = _build_name_param_maps(standard)

        # Eligibility defaults (can be overridden by provided answers)
        building_data = {
            "building_type": answers_by_name.get("building_type", "Commercial"),
            "operational_years": answers_by_name.get("operational_years", 2),
        }

        for name, param in name_to_param.items():
            if name in answers_by_name:
                building_data[param] = answers_by_name[name]
            else:
                itype = name_to_input_type.get(name, "number")
                if itype == "boolean":
                    building_data[param] = False
                else:
                    building_data[param] = 0

        result = calculator.evaluate_enhanced(building_data)
        if result.get("eligible", True):
            result["credit_details"] = result.pop("credit_scores")
        return result
    except Exception as e:
        return {"error": str(e)}
