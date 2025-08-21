import json
from typing import Dict, Any, Union

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

    def evaluate(self, building_data):
        eligible, reason = self.check_eligibility(building_data)
        if not eligible:
            return {"eligible": False, "reason": reason}

        total_score, category_scores, credit_scores = self.calculate_total_score(building_data)
        level = self.get_certification_level(total_score)

        return {
            "eligible": True,
            "total_score": total_score,
            "category_scores": category_scores,
            "credit_scores": credit_scores,
            "certification_level": level
        }

    def evaluate_enhanced(self, building_data):
        eligible, reason = self.check_eligibility(building_data)
        if not eligible:
            return {"eligible": False, "reason": reason}

        total_score, category_scores, credit_scores = self.calculate_total_score(building_data)
        level = self.get_certification_level(total_score)

        return {
            "eligible": True,
            "total_score": total_score,
            "category_scores": category_scores,
            "credit_scores": credit_scores,
            "certification_level": level,
            "detailed_results": credit_scores
        }



def build_name_to_param_map(standard: Union[str, dict]) -> dict:
    """Build mapping from standard input names to paramX keys."""
    if isinstance(standard, str):
        standard = json.loads(standard)
    
    name_to_param = {}
    
    for category in standard["categories"]:
        for credit in category["credits"]:
            calc = credit["calculation"]
            calc_type = calc["type"]
            
            if calc_type == "conditional_sum":
                for condition in calc["conditions"]:
                    name_to_param[condition["name"]] = condition["param"]
            
            elif calc_type == "either_or":
                for option in calc["options"]:
                    for condition in option.get("conditions", []):
                        name_to_param[condition["name"]] = condition["param"]
            
            elif calc_type == "range_based":
                name_to_param[calc["name"]] = calc["param"]
            
            elif calc_type == "composite_sum":
                for part in calc["parts"]:
                    name_to_param[part["name"]] = part["param"]
            
            elif calc_type == "single_condition":
                name_to_param[calc["condition"]["name"]] = calc["condition"]["param"]
                if "additional_requirements" in calc:
                    ar = calc["additional_requirements"]
                    name_to_param[ar["name"]] = ar["param"]
    
    return name_to_param


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
        
        # Check if building is eligible
        if not result.get("eligible", True):
            return {
                "eligible": False,
                "reason": result.get("reason", "Building not eligible"),
                "total_score": 0,
                "certification_level": "Not Eligible"
            }
        
        return {
            "eligible": True,
            "total_score": result["total_score"],
            "certification_level": result["certification_level"],
            "category_scores": result["category_scores"],
            "credit_details": result["credit_scores"]
        }
        
    except Exception as e:
        return {"error": str(e)}


# Example usage
if __name__ == "__main__":
    # Test the simplified function
    test_data = {
        "dry_waste_reduction_percent": 25,
        "wet_waste_composted_percent": 80,
        "potable_water_savings_percent": 35
    }
    
    result = calculate_green_score(test_data)
    print(json.dumps(result, indent=2))
