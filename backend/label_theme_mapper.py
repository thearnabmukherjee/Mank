# label_theme_mapper.py

# label_theme_agent.py

from langgraph.graph import StateGraph
from typing import Dict, List
from openai import OpenAI

# Initialize OpenAI
client = OpenAI(api_key="YOUR_OPENAI_KEY")  


# ---------------------------------------------------------------------------------------------------GPT_CONTENT-------------->


LABEL_THEME_MAP = {
    "Patient Compliance": "Patient Engagement",
    "Missed Dosage": "Patient Engagement",
    "Doctor Resistance": "Adoption Challenges",
    "Patient Feedback": "Patient Engagement",
    "MR Suggestion": "Sales Strategy",
    "Prescription Confirmation": "Sales Strategy",
    "Product Comparison": "Competitive Positioning",
    "Cost Concern": "Pricing Strategy",
    "Pricing Advantage": "Pricing Strategy",
    "Branding and Packaging": "Marketing Effectiveness",
    "Visual Aid Feedback": "Marketing Effectiveness",
    "Rapid Efficacy Advantage": "Clinical Performance",
    "Robust Safety Profile": "Clinical Performance",
    "Doctor's Suggestion": "Clinical Preference",
    "Promotion Request": "Marketing Needs",
    "Supply Concern": "Operational Efficiency",
    "Availability Issue": "Operational Efficiency",
    "Product Quality": "Operational Efficiency",
    "Product Recall": "Operational Efficiency",
    # Add more mappings as your taxonomy grows
}

# -------------------------------------------------------------------------------->
POSSIBLE_THEMES = [
    "Patient Engagement",
    "Patient Compliance",
    "Pricing Strategy",
    "Clinical Performance",
    "Marketing Effectiveness",
    "Sales Strategy",
    "Operational Efficiency",
    "Adoption Challenges",
    "Competitive Positioning",

    "Other"
]


# Node 1: Check known mapping
def check_known_labels(state: Dict[str, str]) -> Dict:
    label = state["label"]
    theme = LABEL_THEME_MAP.get(label)
    if theme:
        return {"label": label, "theme": theme, "source": "cache"}
    return {"label": label}

# Node 2: LLM-based classification
def classify_label_with_llm(state: Dict) -> Dict:
    label = state["label"]
    prompt = f"""
You are a pharmaceutical business analyst.

I will give you a business label extracted from medical transcripts. Classify it under one of the following high-level themes:
- Patient Engagement
- Pricing Strategy
- Clinical Performance
- Marketing Effectiveness
- Sales Strategy
- Operational Efficiency
- Adoption Challenges
- Competitive Positioning
- Other

Label: "Prescription Confirmation"

Respond only with the matching theme name.

Classify the label "{label}" into one of the following themes:
{', '.join(POSSIBLE_THEMES)}.

Respond only with the theme name.
"""
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    theme = response.choices[0].message.content.strip()
    return {"label": label, "theme": theme, "source": "llm"}

# Node 3: Optional dynamic map update
def update_theme_map(state: Dict) -> Dict:
    label = state["label"]
    theme = state["theme"]
    if label not in LABEL_THEME_MAP:
        LABEL_THEME_MAP[label] = theme
    return {"label": label, "theme": theme, "source": state.get("source", "llm"), "status": "mapped"}

# Build LangGraph agent
def build_label_theme_graph():
    builder = StateGraph()

    builder.add_node("check_known", check_known_labels)
    builder.add_node("classify", classify_label_with_llm)
    builder.add_node("update_map", update_theme_map)

    builder.set_entry_point("check_known")

    builder.add_conditional_edges(
    "check_known",
        {
            lambda state: state.get("theme") is None: "classify",
            lambda state: state.get("theme") is not None: "end"
        }
    )

    builder.add_edge("classify", "update_map")

    return builder.compile()



# ------------------------------------------------------------------------------------------------------------------------->





def map_label_to_theme(label: str) -> str:
    """Returns the theme name for a given label or 'Uncategorized' if not mapped."""
    return LABEL_THEME_MAP.get(label, "Uncategorized")

def group_labels_by_theme(label_data: dict) -> dict:
    """
    Groups labels into themes.
    
    Args:
        label_data: {
            "Label1": { "count": X, "reasons": [...], "actions": [...], "sample_texts": [...] },
            ...
        }

    Returns:
        {
            "Theme A": [ {label info...}, ... ],
            "Theme B": [ {label info...}, ... ]
        }
    """
    grouped = {}

    for label, data in label_data.items():
        theme = map_label_to_theme(label)
        if theme not in grouped:
            grouped[theme] = []
        
        grouped[theme].append({
            "label": label,
            "count": data.get("count", 0),
            "reasons": data.get("reasons", []),
            "actions": data.get("actions", []),
            "sample_texts": data.get("sample_texts", [])
        })

    return grouped











# # label_theme_mapper.py
# import logging
# import sys
# from typing import Dict, List, Optional, TypedDict
# from openai import OpenAI
# from langgraph.graph import StateGraph, END

# # Configure logging
# logging.basicConfig(
#     level=logging.DEBUG,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     stream=sys.stdout
# )
# logger = logging.getLogger(__name__)

# # Initialize OpenAI with timeout
# client = OpenAI(
#     api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.UbTFbzO_ffLcFkXEbqeycjT1MEz0UEQCEmk9wm8VZ6k",  # Replace with your actual API key
#     timeout=30.0
# )

# # Define state type
# class LabelState(TypedDict):
#     label: str
#     theme: Optional[str]
#     source: Optional[str]
#     description: Optional[str]
#     subthemes: Optional[List[str]]
#     error: Optional[str]
#     status: Optional[str]

# # Enhanced theme mapping
# LABEL_THEME_MAP = {
#     # Clinical Performance
#     "Rapid Efficacy Advantage": "Clinical Performance",
#     "Robust Safety Profile": "Clinical Performance",
#     "Side Effects Reported": "Clinical Performance",
#     "Dosage Effectiveness": "Clinical Performance",
#     "Clinical Trial Results": "Clinical Performance",
    
#     # Patient Engagement
#     "Patient Compliance": "Patient Engagement",
#     "Missed Dosage": "Patient Engagement",
#     "Patient Feedback": "Patient Engagement",
#     "Adherence Issues": "Patient Engagement",
#     "Patient Education Need": "Patient Engagement",
    
#     # Sales Strategy
#     "MR Suggestion": "Sales Strategy",
#     "Prescription Confirmation": "Sales Strategy",
#     "Doctor Engagement": "Sales Strategy",
#     "Sales Target": "Sales Strategy",
#     "Promotion Effectiveness": "Sales Strategy",
    
#     # Pricing Strategy
#     "Cost Concern": "Pricing Strategy",
#     "Pricing Advantage": "Pricing Strategy",
#     "Reimbursement Issue": "Pricing Strategy",
#     "Price Comparison": "Pricing Strategy",
#     "Discount Request": "Pricing Strategy",
    
#     # Marketing Effectiveness
#     "Branding and Packaging": "Marketing Effectiveness",
#     "Visual Aid Feedback": "Marketing Effectiveness",
#     "Promotion Request": "Marketing Effectiveness",
#     "Marketing Material Feedback": "Marketing Effectiveness",
#     "Campaign Effectiveness": "Marketing Effectiveness",
    
#     # Operational Efficiency
#     "Supply Concern": "Operational Efficiency",
#     "Availability Issue": "Operational Efficiency",
#     "Product Quality": "Operational Efficiency",
#     "Product Recall": "Operational Efficiency",
#     "Distribution Challenge": "Operational Efficiency",
    
#     # Competitive Positioning
#     "Product Comparison": "Competitive Positioning",
#     "Market Share": "Competitive Positioning",
#     "Competitor Activity": "Competitive Positioning",
#     "Differentiation Need": "Competitive Positioning",
    
#     # Adoption Challenges
#     "Doctor Resistance": "Adoption Challenges",
#     "Prescription Habit": "Adoption Challenges",
#     "Therapeutic Area Challenge": "Adoption Challenges",
#     "Guideline Compliance": "Adoption Challenges",
    
#     # Digital Transformation
#     "Digital Engagement": "Digital Transformation",
#     "E-detailing Feedback": "Digital Transformation",
#     "Telemedicine Mention": "Digital Transformation",
    
#     # Light Version
#     "Light Version Launch": "Product Expansion"
# }

# # Theme hierarchy with descriptions
# THEME_HIERARCHY = {
#     "Clinical Performance": {
#         "description": "Drug efficacy, safety, and clinical outcomes",
#         "subthemes": ["Efficacy", "Safety", "Dosing", "Clinical Evidence"]
#     },
#     "Patient Engagement": {
#         "description": "Patient-related factors affecting medication use",
#         "subthemes": ["Adherence", "Education", "Experience", "Compliance"]
#     },
#     "Sales Strategy": {
#         "description": "Sales force effectiveness and prescription behaviors",
#         "subthemes": ["Field Force", "Prescription Drivers", "HCP Engagement"]
#     },
#     "Pricing Strategy": {
#         "description": "Pricing, reimbursement, and cost-related factors",
#         "subthemes": ["Pricing", "Reimbursement", "Value Perception"]
#     },
#     "Marketing Effectiveness": {
#         "description": "Marketing materials and promotional effectiveness",
#         "subthemes": ["Promotions", "Materials", "Branding", "Messaging"]
#     },
#     "Operational Efficiency": {
#         "description": "Supply chain and operational factors",
#         "subthemes": ["Supply Chain", "Quality", "Distribution"]
#     },
#     "Competitive Positioning": {
#         "description": "Market position relative to competitors",
#         "subthemes": ["Differentiation", "Market Share", "Competitor Activity"]
#     },
#     "Adoption Challenges": {
#         "description": "Barriers to physician adoption",
#         "subthemes": ["Physician Resistance", "Guidelines", "Therapeutic Area"]
#     },
#     "Digital Transformation": {
#         "description": "Digital engagement and technology adoption",
#         "subthemes": ["E-detailing", "Telemedicine", "Digital Tools"]
#     },
#     "Product Expansion": {
#         "description": "New product versions or formulations",
#         "subthemes": ["New Formulations", "Line Extensions"]
#     },
#     "Other": {
#         "description": "Uncategorized topics",
#         "subthemes": []
#     }
# }

# def get_theme_description(theme: str) -> str:
#     """Get description for a theme"""
#     return THEME_HIERARCHY.get(theme, {}).get("description", "No description available")

# def get_theme_subthemes(theme: str) -> List[str]:
#     """Get subthemes for a given theme"""
#     return THEME_HIERARCHY.get(theme, {}).get("subthemes", [])

# def check_known_labels(state: LabelState) -> LabelState:
#     """Check if label exists in predefined mapping"""
#     try:
#         label = state["label"]
#         if not label:
#             logger.error("Received empty label")
#             return {**state, "error": "Empty label", "status": "failed"}
        
#         theme = LABEL_THEME_MAP.get(label)
#         if theme:
#             logger.debug(f"Cache hit for label: {label}")
#             return {
#                 **state,
#                 "theme": theme,
#                 "source": "cache",
#                 "description": get_theme_description(theme),
#                 "subthemes": get_theme_subthemes(theme),
#                 "status": "mapped"
#             }
#         logger.debug(f"No cache for label: {label}")
#         return state
#     except Exception as e:
#         logger.error(f"Error in check_known_labels: {str(e)}")
#         return {**state, "error": str(e), "status": "failed"}

# def classify_label_with_llm(state: LabelState) -> LabelState:
#     """Classify label using LLM"""
#     try:
#         label = state["label"]
#         if not label:
#             return {**state, "error": "Empty label", "status": "failed"}
        
#         prompt = f"""
# You are a pharmaceutical business analyst. Classify this label into one of these themes:
# {list(THEME_HIERARCHY.keys())}

# Rules:
# 1. Choose the most specific theme
# 2. Consider typical business context
# 3. Respond ONLY with the theme name

# Examples:
# "Cost Concern" → "Pricing Strategy"
# "Doctor Resistance" → "Adoption Challenges"

# Label to classify: "{label}"
# """
#         logger.debug(f"Classifying label with LLM: {label}")
        
#         response = client.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0,
#             max_tokens=50,
#             timeout=15.0
#         )
        
#         theme = response.choices[0].message.content.strip()
#         logger.debug(f"LLM returned theme: {theme}")
        
#         # Validate theme
#         if theme not in THEME_HIERARCHY:
#             logger.warning(f"Invalid theme from LLM: {theme}, defaulting to Other")
#             theme = "Other"
            
#         return {
#             **state,
#             "theme": theme,
#             "source": "llm",
#             "description": get_theme_description(theme),
#             "subthemes": get_theme_subthemes(theme),
#             "status": "mapped"
#         }
#     except Exception as e:
#         logger.error(f"LLM classification failed: {str(e)}")
#         return {**state, "error": str(e), "status": "failed"}

# def build_label_theme_graph():
#     """Build the classification workflow with proper state management"""
#     workflow = StateGraph(LabelState)

#     # Add nodes
#     workflow.add_node("check_known", check_known_labels)
#     workflow.add_node("classify", classify_label_with_llm)

#     # Set entry point
#     workflow.set_entry_point("check_known")

#     # Add conditional edges
#     workflow.add_conditional_edges(
#         "check_known",
#         lambda state: "classify" if not state.get("theme") else END
#     )

#     # Add final edge
#     workflow.add_edge("classify", END)

#     return workflow.compile()

# def map_label_to_theme(label: str) -> Dict:
#     """Map a single label to its theme with full error handling"""
#     if not label:
#         logger.error("Empty label provided")
#         return {
#             "error": "Empty label",
#             "status": "failed"
#         }
    
#     try:
#         workflow = build_label_theme_graph()
#         result = workflow.invoke({
#             "label": label,
#             "theme": None,
#             "source": None,
#             "description": None,
#             "subthemes": None,
#             "error": None,
#             "status": None
#         })
        
#         if result.get("error"):
#             logger.error(f"Failed to map {label}: {result.get('error')}")
        
#         return {
#             "label": label,
#             "theme": result.get("theme", "Other"),
#             "source": result.get("source", "unknown"),
#             "description": result.get("description", ""),
#             "subthemes": result.get("subthemes", []),
#             "status": result.get("status", "failed")
#         }
#     except Exception as e:
#         logger.error(f"Workflow failed for {label}: {str(e)}")
#         return {
#             "label": label,
#             "error": str(e),
#             "status": "failed"
#         }

# def group_labels_by_theme(label_data: dict) -> dict:
#     """Group multiple labels by theme with comprehensive error handling"""
#     if not label_data:
#         logger.error("No label data provided")
#         return {"error": "No labels to process"}
    
#     results = {}
#     try:
#         for label, data in label_data.items():
#             if not isinstance(data, dict):
#                 logger.warning(f"Invalid data format for label {label}")
#                 continue
                
#             mapping = map_label_to_theme(label)
#             theme = mapping.get("theme", "Other")
            
#             if theme not in results:
#                 results[theme] = {
#                     "description": mapping.get("description", ""),
#                     "subthemes": mapping.get("subthemes", []),
#                     "labels": []
#                 }
            
#             results[theme]["labels"].append({
#                 "label": label,
#                 "count": data.get("count", 0),
#                 "reasons": data.get("reasons", []),
#                 "actions": data.get("actions", []),
#                 "sample_texts": data.get("sample_texts", []),
#                 "mapping_info": {
#                     "source": mapping.get("source"),
#                     "status": mapping.get("status")
#                 }
#             })
        
#         # Sort by label count
#         for theme in results:
#             results[theme]["labels"].sort(key=lambda x: x.get("count", 0), reverse=True)
#             results[theme]["total_count"] = sum(label.get("count", 0) for label in results[theme]["labels"])
        
#         # Sort themes by total count
#         results = dict(sorted(
#             results.items(),
#             key=lambda item: item[1]["total_count"],
#             reverse=True
#         ))
        
#         return results
        
#     except Exception as e:
#         logger.error(f"Error in group_labels_by_theme: {str(e)}")
#         return {"error": str(e)}

# # Test function
# def test_mapping():
#     """Test the label mapping functionality"""
#     test_data = {
#         "Cost Concern": {"count": 15, "reasons": ["Too expensive"]},
#         "Patient Compliance": {"count": 8, "reasons": ["Forgot to take"]},
#         "Light Version Launch": {"count": 5, "reasons": ["New product version"]},
#         "Invalid Label": "This should be skipped"
#     }
    
#     print("\nTesting label theme mapping...")
#     print("Input data:", test_data)
    
#     result = group_labels_by_theme(test_data)
#     print("\nResults:")
#     import pprint
#     pprint.pprint(result)

# if __name__ == "__main__":
#     test_mapping()