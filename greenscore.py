from dataclasses import dataclass, field
from typing import Optional, Literal, Dict, Any
import json

@dataclass
class GreenScoreInput:
    """
    Strongly-typed input for GreenScoreCalculator.

    Use this class to define and validate the data your frontend must collect.
    Call to_calculator_payload() to transform into the dict expected by the
    current calculator (using param1..param13 keys).
    """
    # Eligibility
    building_type: Literal["Institutional", "Commercial"] = field(metadata={
        "label": "Building Type",
        "description": "Select the building category as per eligibility",
    })
    operational_years: int = field(metadata={
        "label": "Operational Years",
        "description": "Number of years the building has been operational",
        "units": "years"
    })

    # SF1 – Enhanced Waste Management
    dry_waste_reduction_percent: Optional[float] = field(default=None, metadata={
        "label": "Dry waste reduction percentage compared to last year",
        "units": "percent"
    })
    dry_waste_recycled_percent: Optional[float] = field(default=None, metadata={
        "label": "Dry waste recycled percentage",
        "units": "percent"
    })
    wet_waste_composted_percent: Optional[float] = field(default=None, metadata={
        "label": "Wet waste composted percentage",
        "description": "Percentage amount of wet waste composted in the facility last year",
        "units": "percent"
    })

    # SF2 – Sustainable Retrofitting
    eco_labelled_product_cost_percent: Optional[float] = field(default=None, metadata={
        "label": "Eco-labelled product cost percentage during retrofitting",
        "units": "percent"
    })
    certified_green_products_count: Optional[float] = field(default=None, metadata={
        "label": "Number of certified green products used",
        "units": "count"
    })
    sustainable_procurement_policy: Optional[bool] = field(default=None, metadata={
        "label": "Does the building have a sustainable procurement policy?"
    })

    # SF3 – Urban Heat Island Mitigation
    roof_uhi_coverage_percent: Optional[float] = field(default=None, metadata={
        "label": "Roof area with high SRI/green/reflective/solar coverage (% of total roof area)",
        "units": "percent"
    })
    non_roof_uhi_coverage_percent: Optional[float] = field(default=None, metadata={
        "label": "Non-roof hardscape with high SRI/green/reflective/shaded coverage (% of total non-roof hardscape)",
        "units": "percent"
    })

    # SF4 – Eco-friendly Landscaping Practices
    organic_fertilizer_coverage_percent: Optional[float] = field(default=None, metadata={
        "label": "Landscape maintained with organic fertilizers/soil conditioners (% of landscaped area)",
        "units": "percent"
    })
    landscape_area_percent: Optional[float] = field(default=None, metadata={
        "label": "Landscaped area as % of total site area",
        "units": "percent"
    })

    # SF5 – Eco-friendly Commuting Practices
    public_transport_compliant: Optional[bool] = field(default=None, metadata={
        "label": "Is the site within 800 m of public transport and serves >=60% occupants?"
    })
    shuttle_service_coverage_percent: Optional[float] = field(default=None, metadata={
        "label": "Shuttle service coverage (% of total occupants)",
        "units": "percent"
    })

    # WC1 – Enhanced Water Efficiency
    potable_water_savings_percent: Optional[float] = field(default=None, metadata={
        "label": "Potable water savings percentage over baseline",
        "units": "percent"
    })

    # EE1 – Enhanced Eco-friendly Refrigerants & Fire Suppression Management System
    gwp_refrigerants_fire_suppression: Optional[float] = field(default=None, metadata={
        "label": "Average GWP of all refrigerants/substances and fire suppression systems used in the building",
        "units": "GWP"
    })

    def to_calculator_payload(self) -> Dict[str, Any]:
        """
        Convert to the dict expected by GreenScoreCalculator where credit inputs
        are keyed by param1..param14, as defined in advant_standard.json.
        """
        return {
            # Eligibility
            "building_type": self.building_type,
            "operational_years": self.operational_years,

            # Param mapping as per advant_standard.json
            # SF1
            "param1": self.dry_waste_reduction_percent,
            "param2": self.dry_waste_recycled_percent,
            "param3": self.wet_waste_composted_percent,

            # SF2
            "param4": self.eco_labelled_product_cost_percent,
            "param5": self.certified_green_products_count,
            "param6": self.sustainable_procurement_policy,

            # SF3
            "param7": self.roof_uhi_coverage_percent,
            "param8": self.non_roof_uhi_coverage_percent,

            # SF4
            "param9": self.organic_fertilizer_coverage_percent,
            "param10": self.landscape_area_percent,

            # SF5
            "param11": self.public_transport_compliant,
            "param12": self.shuttle_service_coverage_percent,

            # WC1
            "param13": self.potable_water_savings_percent,

            # EE1
            "param14": self.gwp_refrigerants_fire_suppression,
        }

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
                min_val = r.get("min")
                max_val = r.get("max")
                
                # Check if value falls within range
                min_ok = min_val is None or val >= min_val
                max_ok = max_val is None or val <= max_val
                
                if min_ok and max_ok:
                    return r["points"]
            return 0
        
        elif calc_type == "composite_sum":
            score = 0
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
                credit_scores[credit["sub_id"]] = points
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

    building_data = GreenScoreInput(
        building_type="Commercial",
        operational_years=2,
        dry_waste_reduction_percent=25,
        dry_waste_recycled_percent=100,
        wet_waste_composted_percent=90,
        eco_labelled_product_cost_percent=15,
        certified_green_products_count=4,
        sustainable_procurement_policy=True,
        potable_water_savings_percent=35
    ).to_calculator_payload()

    result = calc.evaluate(building_data)
    print(json.dumps(result, indent=2))
