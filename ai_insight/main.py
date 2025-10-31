import os
import json
import google.generativeai as genai
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any
from dotenv import load_dotenv
import traceback

# --- 1. INITIAL SETUP & CONFIGURATION ---

app = FastAPI(
    title="Smart Budget Analyzer API",
    description="An API that uses Google Gemini to analyze budget data and provide financial advice.",
    version="1.8.0",  # Final Corrected Version
)

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

# --- 3. PROMPT TEMPLATE ---

PROMPT_TEMPLATE = """
You are a professional and clear-spoken financial advisor AI. Your tone should be assertive but nice, providing direct, actionable advice in a respectful and non-judgmental manner. Your advice must be delivered as clear statements, not questions.

Analyze the following budget categories:
'FOOD_DINING', 'TRANSPORTATION', 'BILLS_UTILITIES', 'ENTERTAINMENT', 'HEALTH_FITNESS', 'EDUCATION', 'SHOPPING', 'GROCERY'.

{critical_alert_section}

Tasks:
1. For each category, calculate the percentage spent and classify as:
   - "On Track" (≤ 75%)
   - "High Spending" (>75% and ≤100%)
   - "Overspent" (>100%)
2. Identify the top 2 financial issues.
3. Based on the most critical issue, provide **one single, clear AI recommendation** using the professional tone and logic described below.

**Recommendation Logic and Tone (Assertive but Nice):
- If a category is 'Overspent': State the problem directly and provide a clear two-step solution in a single sentence. For example: "Your Entertainment category is over budget; the immediate priority is to halt further spending in this area, and the recommended next step is to re-evaluate its budget for the next period to ensure it's realistic."
- If the main issue is 'High Spending': State the observation clearly and recommend a specific action. For example: "Spending in the Bills & Utilities category is high. It is important to monitor this category closely for the remainder of the period to stay within the allocated budget."
- If all categories are 'On Track': Acknowledge the success professionally and recommend a strategic action for the surplus. For example: "Your budget is being managed effectively. A strategic next step is to allocate the surplus funds towards a specific financial goal, such as savings or investments."**

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
  "ai_recommendations": ["A single, assertive but respectful recommendation"]
}}
"""

# --- 4. ENDPOINT IMPLEMENTATION ---

@app.post("/analyze-budget", response_model=Dict[str, Any])
async def analyze_budget(budget_input: BudgetInput):
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
            response_mime_type="application/json"
        )
        model = genai.GenerativeModel(
            "gemini-2.5-flash",
            generation_config=generation_config
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

@app.get("/")
def read_root():
    return {"status": "Budget Analyzer API is running"}