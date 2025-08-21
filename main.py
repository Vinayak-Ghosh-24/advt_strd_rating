import json
from greenscore import calculate_green_score

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

def main():
    print("=== Advant Green Building Evaluation ===")
    
    # Collect credit data using simplified variable names
    data = {}
    
    # Ask questions for each credit variable
    data["dry_waste_reduction_percent"] = ask_numeric("Dry waste reduction percentage compared to last year", optional=True)
    data["dry_waste_recycled_percent"] = ask_numeric("Dry waste recycled percentage", optional=True)
    data["wet_waste_composted_percent"] = ask_numeric("Wet waste composted percentage", optional=True)
    data["eco_labelled_product_cost_percent"] = ask_numeric("Eco-labelled product cost percentage during retrofitting", optional=True)
    data["certified_green_products_count"] = ask_numeric("Number of certified green products used", optional=True)
    data["sustainable_procurement_policy"] = ask_yes_no("Does the building have a sustainable procurement policy?", optional=True)
    data["roof_uhi_coverage_percent"] = ask_numeric("Roof area with high SRI/green/reflective/solar coverage (% of total roof area)", optional=True)
    data["non_roof_uhi_coverage_percent"] = ask_numeric("Non-roof hardscape with high SRI/green/reflective/shaded coverage (%)", optional=True)
    data["organic_fertilizer_coverage_percent"] = ask_numeric("Landscape maintained with organic fertilizers/soil conditioners (%)", optional=True)
    data["landscape_area_percent"] = ask_numeric("Landscaped area as % of total site area", optional=True)
    data["public_transport_compliant"] = ask_yes_no("Is the site within 800m of public transport and serves >=60% occupants?", optional=True)
    data["shuttle_service_coverage_percent"] = ask_numeric("Shuttle service coverage (% of total occupants)", optional=True)
    data["potable_water_savings_percent"] = ask_numeric("Potable water savings percentage over baseline", optional=True)
    data["gwp_refrigerants_fire_suppression"] = ask_numeric("Average GWP of all refrigerants/substances and fire suppression systems", optional=True)
    
    # Remove None values
    data = {k: v for k, v in data.items() if v is not None}
    
    # Calculate score using simplified function
    result = calculate_green_score(data)
    
    print("\n=== Evaluation Result ===")
    if "error" in result:
        print(f"Error: {result['error']}")
        return
        
    print(f"Total Green Score: {result['total_score']}")
    print(f"Certification Level: {result['certification_level']}")
    
    print("\nCategory Scores:")
    for category_id, score in result['category_scores'].items():
        print(f" - {category_id}: {score} points")
    
    print("\nCredit Details:")
    for credit_id, details in result['credit_details'].items():
        print(f" - {credit_id}: {details['points']} points")
        for condition in details['conditions']:
            status = "✓" if condition['result'] else "✗"
            print(f"   {status} {condition['condition']}: {condition['points']} pts")

if __name__ == "__main__":
    main()
