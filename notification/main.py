from fastapi import FastAPI
import uvicorn
import google.generativeai as genai
from dotenv import load_dotenv
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict
from fastapi.responses import RedirectResponse
from fastapi import APIRouter
import os
import json
import re

# --------------------------
# Load environment variables
# --------------------------
load_dotenv()

router = APIRouter(prefix="/notification", tags=["Notification"])

@router.get("/", include_in_schema=False) 
async def root():
    return RedirectResponse(url="/docs")

# Initialize FastAPI app

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

app = FastAPI(title="Financial Transaction Analyzer")

# --------------------------
# Pydantic models
# --------------------------
class Notification(BaseModel):
    name: str
    intent: Optional[str] = None
    timestamp: datetime

class NotificationJSON(BaseModel):
    id: str
    packageName: str
    appName: str
    title: str
    text: str
    bigText: Optional[str] = None
    subText: Optional[str] = None
    summaryText: Optional[str] = None
    timestamp: int
    category: Optional[str] = None
    priority: int
    flags: int
    group: Optional[str] = None
    tag: Optional[str] = None
    actions: List[Notification] = []
    largeIcon: Optional[str] = None
    smallIcon: Optional[str] = None
    color: int
    visibility: int
    extras: Dict[str, str] = {}
    isOngoing: bool
    isClearable: bool
    isGroup: bool
    isGroupSummary: bool
    isRemoved: bool = False
    createdAt: Optional[datetime] = datetime.now()
    removedAt: Optional[datetime] = None

class OCRJSON(NotificationJSON):
    """
    OCR JSON schema for financial transactions:
    - merchant_name
    - merchant_contact
    - transaction_date
    - transaction_time
    - total_amount
    - subtotal_amount
    - discount_amount
    - tax
    - category
    - items: list of {quantity, item_name, item_price}
    """
    pass

class RequestBody(BaseModel):
    notification: NotificationJSON
    ocrJson: Optional[OCRJSON] = None

# --------------------------
# System prompt
# --------------------------
system_prompt = """
Analyze the following Notification JSON and determine if it represents a financial transaction (expense/money sent/withdrawn).

If it is a financial transaction, extract all relevant details and return ONLY a valid JSON in this exact OCR schema:

{
  "merchant_name": "store/restaurant/pharmacy name or null",
  "merchant_contact": "phone number or contact info or null",
  "transaction_date": "date in YYYY-MM-DD format or null",
  "transaction_time": "time in HH:MM:SS (24-hour) format or null if not visible",
  "total_amount": "total amount as number or null",
  "subtotal_amount": "subtotal amount as number or null",
  "discount_amount": "discount amount as number or null",
  "tax": "tax amount as number or null",
  "category": "FOOD_DINING, TRANSPORTATION, BILLS_UTILITIES, GROCERY, ENTERTAINMENT, HEALTH_FITNESS, EDUCATION, SHOPPING, OTHER/GENERAL",
  "items": [
    {
      "quantity": "number of items or 1 if not specified",
      "item_name": "item name/description",
      "item_price": "price per item or total price"
    }
  ]
}

Rules:
- If the notification is NOT a financial transaction (no money sent/withdrawn/paid), return null.
- Preserve the exact sign of all amounts from the notification/OCR.
- Use null for any missing or unavailable fields.
- Category should be inferred contextually.
- Do NOT include markdown, explanations, or extra text.

"""

# --------------------------
# Endpoint
# --------------------------
@router.post("/analyze-notification")
async def analyze_notification(body: RequestBody):
    # Provide empty OCR if missing
    ocr_json = body.ocrJson or OCRJSON(
        id="",
        packageName="",
        appName="",
        title="",
        text="",
        timestamp=int(datetime.now().timestamp()),
        priority=0,
        flags=0,
        color=0,
        visibility=1,
        actions=[],
        isOngoing=False,
        isClearable=True,
        isGroup=False,
        isGroupSummary=False
    )

    prompt_text = (
        f"{system_prompt}\n\nNotification JSON:\n{body.notification.json()}\nOCR JSON:\n{ocr_json.json()}"
    )

    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt_text)

    # Clean ```json``` if returned
    raw_text = response.text.strip()
    clean_text = re.sub(r"^```(?:json)?|```$", "", raw_text).strip()
    
    # If LLM returns exactly "{null}", return it directly
    # if clean_text == "{null}" or (isinstance(output_json, dict) and not any(output_json.values())):
    #     return None  # FastAPI will serialize this as JSON null

    try:
        output_json = json.loads(clean_text)
    except json.JSONDecodeError:
        if clean_text in ["{null}", "null"]:
            return None  # Non-financial notification → return JSON null
        return {"error": "Failed to parse model response", "raw_response": clean_text}

    # If all OCR fields are empty → return JSON null
    if isinstance(output_json, dict):
        meaningful_values = [v for v in output_json.values() if v not in [None, "", [], {}]]
        if not meaningful_values:
            return None

    return output_json

# --------------------------
# Run server
# --------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8050, reload=True)
