"""
Configurable business rules for attendance categorization
This file allows easy modification of rules without changing core logic
"""

# Attendance categorization rules
ATTENDANCE_CATEGORIES = {
    "critical": {
        "min": 0,
        "max": 65,
        "label": "Critical",
        "color": "#f44336",
        "description": "Requires immediate attention"
    },
    "danger": {
        "min": 65,
        "max": 75,
        "label": "Not Safe / Danger",
        "color": "#ff9800",
        "description": "At risk of falling below minimum"
    },
    "border": {
        "min": 75,
        "max": 80,
        "label": "Border",
        "color": "#ffc107",
        "description": "Close to safe threshold"
    },
    "safe": {
        "min": 80,
        "max": 100,
        "label": "Safe",
        "color": "#4caf50",
        "description": "Meeting attendance requirements"
    }
}

# Subject code patterns for Theory/Lab detection
SUBJECT_CODE_PATTERNS = {
    "theory_suffix": "T",
    "lab_suffix": "L",
    "combine_when_same_base": True
}

# OD/ML adjustment rules
OD_ML_RULES = {
    "apply_below_percentage": 75.0,
    "include_od": True,
    "include_ml": True,
    "max_adjustment_percentage": 10.0  # Maximum 10% boost from OD/ML
}


def get_category_for_percentage(percentage: float) -> str:
    """
    Determine the category for a given attendance percentage
    
    Args:
        percentage: Attendance percentage (0-100)
        
    Returns:
        Category key (critical, danger, border, safe)
    """
    for category_key, rules in ATTENDANCE_CATEGORIES.items():
        if rules["min"] <= percentage < rules["max"]:
            return category_key
    
    # Default to safe if >= 80
    return "safe"


def get_category_details(category_key: str) -> dict:
    """
    Get full details for a category
    
    Args:
        category_key: Category identifier
        
    Returns:
        Dictionary with category details
    """
    return ATTENDANCE_CATEGORIES.get(category_key, ATTENDANCE_CATEGORIES["safe"])
