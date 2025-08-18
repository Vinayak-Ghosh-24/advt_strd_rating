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
            for cond in credit["calculation"]["conditions"]:
                val = safe_num(building_data.get(cond["param"]))
                if val >= cond["threshold"]:
                    total += cond["points"]
            return min(total, max_points)

        elif calc_type == "either_or":
            points = 0
            
            for option in credit["calculation"]["options"]:
                group_points = 0
                group_max = option.get("points", 1)  # Default to 1 point per group if not specified
                
                # Check all conditions in this group
                for condition in option.get("conditions", []):
                    val = building_data.get(condition["param"])
                    
                    # Check threshold condition
                    if "threshold" in condition and val is not None and val >= condition["threshold"]:
                        group_points = group_max
                        break  # Only need one condition in the group to be true
                        
                    # Check value condition
                    if "value" in condition and building_data.get(condition["param"]) == condition["value"]:
                        group_points = group_max
                        break  # Only need one condition in the group to be true
                
                points += group_points
                
            return min(points, max_points)

        elif calc_type == "range_based":
            val = safe_num(building_data.get(credit["calculation"]["param"]))
            for r in credit["calculation"]["ranges"]:
                if r["min"] is not None and val < r["min"]:
                    continue
                if r["max"] is not None and val > r["max"]:
                    continue
                return r["points"]
            return 0
        
        elif calc_type == "composite_sum":
            score = 0
            for part in credit["calculation"]["parts"]:
                val = safe_num(building_data.get(part["param"]))
                for r in part["ranges"]:
                    if r["min"] is not None and val < r["min"]:
                        continue
                    if r["max"] is not None and val > r["max"]:
                        continue
                    score += r["points"]
                    break
            return min(score, max_points)

        elif calc_type == "single_condition":
            cond = credit["calculation"]["condition"]
            min_req = credit["calculation"].get("additional_requirements", {})
            val = safe_num(building_data.get(cond["param"]))
            min_val = safe_num(building_data.get(min_req.get("param")))
            if val >= cond["threshold"] and min_val >= min_req.get("min_required", 0):
                return cond["points"]
            return 0

        return 0

    def calculate_total_score(self, building_data):
        total_score = 0
        category_scores = {}
        credit_scores = {}

        for category in self.standard["categories"]:
            cat_score = 0
            for credit in category["credits"]:
                points = self.calculate_credit_points(credit, building_data)
                credit_scores[credit["id"]] = points
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


# Example usage
if __name__ == "__main__":
    # Load JSON from file or string
    with open("advant_standard.json") as f:
        standard = json.load(f)

    calc = GreenScoreCalculator(standard)

    building_data = {
        "building_type": "Commercial",
        "operational_years": 2,
        "dry_waste_reduction_percent": 25,
        "dry_waste_recycled_percent": 100,
        "wet_waste_composted_percent": 90,
        "eco_labelled_product_cost_percent": 15,
        "certified_green_products_count": 4,
        "sustainable_procurement_policy": True,
        "potable_water_savings_percent": 35
    }

    result = calc.evaluate(building_data)
    print(json.dumps(result, indent=2))
