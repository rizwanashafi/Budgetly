import os
import json
import google.generativeai as genai
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any, List
from dotenv import load_dotenv
import traceback
from fastapi import APIRouter
from fastapi.responses import RedirectResponse


router = APIRouter(prefix="/ai_insights", tags=["AI Insights"])

LATEST_ANALYSIS_RESULT: Dict[str, Any] = {}

@router.get("/", include_in_schema=False) 
async def root():
    return RedirectResponse(url="/docs")

load_dotenv()

try:
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    genai.configure(api_key=gemini_api_key)
except Exception as e:
    print(f"FATAL: Error configuring Gemini API - {e}")

# --- 2. DEFINE INPUT DATA MODEL (PYDANTIC) ---

class CategoryData(BaseModel):
    current_spent: int = Field(..., example=15000)
    total_budget: int = Field(..., example=20000)

class BudgetInput(BaseModel):
    categories: Dict[str, CategoryData]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "categories": {
                        "FOOD_DINING": {"current_spent": 20000, "total_budget": 40000},
                        "TRANSPORTATION": {"current_spent": 10000, "total_budget": 20000},
                        "BILLS_UTILITIES": {"current_spent": 18500, "total_budget": 20000},
                        "ENTERTAINMENT": {"current_spent": 16000, "total_budget": 15000},
                        "HEALTH_FITNESS": {"current_spent": 5000, "total_budget": 10000},
                        "EDUCATION": {"current_spent": 7000, "total_budget": 12000},
                        "SHOPPING": {"current_spent": 6000, "total_budget": 15000},
                        "GROCERY": {"current_spent": 10000, "total_budget": 20000}
                    }
                }
            ]
        }
    }
class InsightsResponse(BaseModel):
    key_observations: List[str]
    ai_recommendations: List[str]
# --- 3. PROMPT TEMPLATE ---

PROMPT_TEMPLATE = """
You are a friendly and helpful financial assistant. Your tone should be natural, conversational, and encouraging, providing practical, actionable advice in a supportive and non-judgmental manner. Your advice should feel like a helpful suggestion from a friend.

All financial references, including budget amounts and overages, must be expressed in Pakistani Rupees (Rs.).

Analyze the following budget categories:
'FOOD_DINING', 'TRANSPORTATION', 'BILLS_UTILITIES', 'ENTERTAINMENT', 'HEALTH_FITNESS', 'EDUCATION', 'SHOPPING', 'GROCERY'.

{critical_alert_section}

Tasks:
1. For each category, calculate the percentage spent. If the actual spending exceeds the budget, cap the displayed 'percentage_spent' at 100% in the JSON output, but ensure the 'status' accurately reflects if it's 'Overspent'. Classify as:
   - "On Track" (≤ 75%)
   - "High Spending" (>75% and ≤100%)
   - "Overspent" (>100% actual spending)
2. Identify the top 2 financial issues.
3. Based on the most critical issue, provide **one single, clear AI recommendation** using the friendly, conversational tone and logic described below.

**Recommendation Logic and Tone (Friendly and Conversational):
- If a category is 'Overspent': Acknowledge the overspending and suggest practical alternative approaches or solutions. For example: "It looks like your Entertainment spending has gone a bit over budget. Instead of cutting it entirely, perhaps explore free or low-cost activities for the rest of the month, or consider reallocating a small amount from another less critical category if possible, and let's plan a more realistic budget for next time."
- If the main issue is 'High Spending': State the observation clearly and recommend a specific, gentle action. For example: "Your spending in Bills & Utilities is getting a bit high. It might be a good idea to keep a close eye on this category for the rest of the period to help you stay within your budget."
- If all categories are 'On Track': Acknowledge the success warmly and recommend a strategic, encouraging action for the surplus. For example: "Wow, you're doing a fantastic job managing your budget! With some funds left over, how about we think about putting that towards a fun savings goal or even a small investment?"**

Respond **only** with a clean JSON object in this structure:
{{
  "analysis": [
    {{
      "category": "CATEGORY_NAME",
      "percentage_spent": 0.0,
      "status": "On Track | High Spending | Overspent"
    }}
  ],
  "key_observations": ["Observation 1", "Observation 2"],
  "ai_recommendations": ["A single, friendly and conversational recommendation"]
}}
"""

# --- 4. ENDPOINT IMPLEMENTATION ---

@router.post("/analyze-budget", response_model=Dict[str, Any])
async def analyze_budget(budget_input: BudgetInput):
    global LATEST_ANALYSIS_RESULT 
    critical_alert_section = ""
    overspent_categories = []

    for category_name, data in budget_input.categories.items():
        if data.current_spent > data.total_budget:
            overage = data.current_spent - data.total_budget
            overspent_categories.append(f"'{category_name}' is over budget by {overage}")

    if overspent_categories:
        alerts = ", ".join(overspent_categories)
        critical_alert_section = (
            f"!!! URGENT ACTION REQUIRED !!!\n"
            f"The user is over budget in the following categories: {alerts}.\n"
            f"Provide urgent recommendations for these first.\n"
        )

    try:
        # Configure the model to expect a JSON response
        generation_config = genai.types.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.8
        )
        model = genai.GenerativeModel(
            "gemini-2.5-flash",
            generation_config=generation_config,
        )
        
        prompt = PROMPT_TEMPLATE.format(critical_alert_section=critical_alert_section)
        prompt += f"\n\nUser Data:\n{budget_input.model_dump_json(indent=2)}"
        
        response = model.generate_content(prompt)

        if not response.parts or not response.text:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="AI response was empty or filtered by content safety.",
            )

        response_text = response.text.strip()
        
        # Robustly find the start and end of the JSON object to avoid parsing errors
        start_index = response_text.find('{')
        end_index = response_text.rfind('}') + 1

        if start_index == -1 or end_index == 0:
            print(f"ERROR: No valid JSON object found in response: {response_text}")
            raise ValueError("No valid JSON object found in the AI response.")
            
        cleaned_json_str = response_text[start_index:end_index]

        try:
            json_response = json.loads(cleaned_json_str)
            LATEST_ANALYSIS_RESULT = json_response
            # json_response = json.loads(cleaned_json_str)
        except json.JSONDecodeError as e:
            print(f"--- FAILED TO DECODE JSON ---\n{cleaned_json_str}\n--- END OF FAILED STRING ---")
            raise ValueError(f"Invalid JSON format returned: {e}")

        return json_response

    except Exception as e:
        print("\n--- DETAILED SERVER ERROR ---")
        traceback.print_exc()
        print("--- END OF TRACEBACK ---\n")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )

# --- 5. HEALTH CHECK ENDPOINT ---

# @router.get("/")
# def read_root():
#     return {"status": "Budget Analyzer API is running"}
@router.get("/latest-insights", response_model=InsightsResponse)
async def get_latest_insights():
    """
    Retrieve the key observations and AI recommendations from the most recent analysis.
    """
    # Check if a result has been generated yet
    if not LATEST_ANALYSIS_RESULT:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No analysis has been performed yet. Please POST to /analyze-budget first."
        )

    # Create the specific response you want from the stored result
    insights_data = {
        "key_observations": LATEST_ANALYSIS_RESULT.get("key_observations", []),
        "ai_recommendations": LATEST_ANALYSIS_RESULT.get("ai_recommendations", [])
    }

    return insights_data