#!/usr/bin/env python3
"""
FastAPI OCR Application - Simple Automatic OCR Processing
Upload images and get extracted data immediately
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image
import pandas as pd
from OCR.utils import clean_json_string
import json
import os
import uuid
import tempfile
from typing import Dict
from fastapi.responses import RedirectResponse
from fastapi import APIRouter

load_dotenv()

router = APIRouter(prefix="/OCR", tags=["OCR"])

# Initialize FastAPI app

@router.get("/", include_in_schema=False) 
async def root():
    return RedirectResponse(url="/docs")

# In-memory storage for uploaded images and their metadata
uploaded_images: Dict[str, Dict] = {}

# Configure Gemini API
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY environment variable is required")

genai.configure(api_key=gemini_api_key)

# Configure generation settings for better accuracy with blurry/low-quality images
generation_config = {
    "temperature": 0.1,  # Lower temperature for more deterministic/accurate extraction
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
}

model = genai.GenerativeModel(
    'gemini-2.0-flash',
    generation_config=generation_config
)

def get_gemini_prompt():
    """Get the Gemini AI prompt for universal receipt OCR processing"""
    return """You are an OCR assistant that extracts structured data from **receipt images only**.

If the uploaded image is **NOT a receipt**, respond with this exact JSON:
{
  "error": "Invalid image. Please upload a valid receipt for OCR processing."
}

---

### RECEIPT OCR INSTRUCTIONS

If the image **is** a valid receipt, extract the following fields in **standardized JSON** format:

{
  "merchant_name": "store/restaurant/pharmacy name or null",
  "merchant_contact": "phone number or contact info or null",
  "transaction_date": "date in YYYY-MM-DD format or null",
  "transaction_time": "time in HH:MM:SS (24-hour) format or null if not visible",
  "total_amount": "total amount as number (preserve exact sign: positive for credits/refunds, negative for charges/debits) or null",
  "tax": "tax amount as number (preserve exact sign) or null",
  "category": "REQUIRED - Must be one of: FOOD_DINING, TRANSPORTATION, BILLS_UTILITIES, GROCERY, ENTERTAINMENT, HEALTH_FITNESS, EDUCATION, SHOPPING, or OTHER/GENERAL (never null)",
  "items": [
    {
      "quantity": "number of items purchased (as number) or 1 if not specified",
      "item_name": "item name/description",
      "item_price": "price per item or total price for this line (as number, preserve exact sign)"
    }
  ]
}

Do NOT include a "timestamp" field — it will be added automatically by the system.

---

### CRITICAL RULES

**Amount Extraction**
- Preserve the **exact sign** (+ or -) as shown on the receipt.
- Positive → credits/refunds (e.g., "+50.00", "CR 50.00", "REFUND 50.00")
- Negative → charges/debits (e.g., "-50.00", "DR 50.00", "CHARGE 50.00")
- Never modify or infer signs.
- If uncertain or unreadable, return `null`.

**Category Field**
- **Required field**, never null.
- Must be one of:
  - FOOD_DINING — Restaurants, cafes, bars, delivery, etc.
  - TRANSPORTATION — Gas, parking, tolls, public transit, ride-share, auto repair.
  - BILLS_UTILITIES — Electric, water, internet, phone, rent, insurance.
  - GROCERY — Supermarkets, grocery stores, wholesale clubs.
  - ENTERTAINMENT — Movies, concerts, gaming, sports, events.
  - HEALTH_FITNESS — Pharmacies, clinics, gyms, health supplements.
  - EDUCATION — Schools, tuition, books, online courses.
  - SHOPPING — Retail, clothing, electronics, home goods, e-commerce.
  - OTHER/GENERAL — Only if no clear match.
- Infer from **merchant name** and **items list**.
- Examples:
  - "Starbucks", "McDonald's" → FOOD_DINING
  - "Shell Gas", "Chevron" → TRANSPORTATION
  - "Verizon", "Electric Company" → BILLS_UTILITIES
  - "Whole Foods", "Walmart Grocery" → GROCERY
  - "Netflix", "AMC Theaters" → ENTERTAINMENT
  - "CVS Pharmacy", "24 Hour Fitness" → HEALTH_FITNESS
  - "University Bookstore", "Coursera" → EDUCATION
  - "Target", "Amazon", "Best Buy" → SHOPPING

**Date & Time Extraction**
- Extract `transaction_date` in `YYYY-MM-DD`.
- Extract `transaction_time` in `HH:MM:SS` (24-hour format).
- Convert 12-hour format to 24-hour if necessary.
- If only hours/minutes visible, append “:00”.
- If time not visible → `null`.

Examples:
- "2:30 PM" → "14:30:00"
- "09:45" → "09:45:00"
- "23:15:30" → "23:15:30"

---

### GENERAL INSTRUCTIONS
- Use null for any missing or unclear fields, except for the category field — it should never be null.
- If the receipt does not explicitly mention a category, infer and return the most appropriate category based on the receipt content.
- Return **only valid JSON**, no markdown or extra text.
- Do **not** mix error responses with receipt data.

---
Important: Extract all the information that is clearly visible and readable as well as blurry on the receipt image. Focus on accuracy over completeness. NEVER modify the sign of any monetary amount. ALWAYS provide a category from the predefined list (use "OTHER" if uncertain)."""

def process_image_with_gemini(image: Image.Image) -> str:
    """Process image with Gemini API to extract structured JSON"""
    prompt = get_gemini_prompt()
    response = model.generate_content([prompt, image])
    return response.text

def validate_image_file(file: UploadFile) -> bool:
    """Validate uploaded image file"""
    allowed_types = ["image/png", "image/jpeg", "image/jpg"]
    return file.content_type in allowed_types


@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...)
):
    """
    Upload an image file and automatically extract OCR data

    Args:
        file: Image file (PNG, JPG, JPEG)

    Returns:
        JSON response with extracted OCR data and image ID
    """
    # Validate image file
    if not validate_image_file(file):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PNG, JPG, and JPEG files are allowed."
        )

    try:
        # Generate unique image ID
        image_id = str(uuid.uuid4())
        image_data = await file.read()

        # Create temporary file to store the image
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, f"ocr_image_{image_id}.jpg")

        # Save image to temporary file
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(image_data)

        # Load image for processing
        image = Image.open(temp_file_path)
        extracted_json = process_image_with_gemini(image)

        # Clean and parse JSON
        cleaned_json = clean_json_string(extracted_json)

        if not cleaned_json.strip():
            # Clean up temporary file on error
            try:
                os.remove(temp_file_path)
            except:
                pass

            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Extracted data appears to be empty after cleaning",
                    "original_data": extracted_json,
                    "cleaned_data": cleaned_json
                }
            )

        # Parse JSON data
        try:
            parsed_data = json.loads(cleaned_json)
        except json.JSONDecodeError as e:
            # Clean up temporary file on error
            try:
                os.remove(temp_file_path)
            except:
                pass

            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": f"Invalid JSON format: {str(e)}",
                    "original_data": extracted_json,
                    "cleaned_data": cleaned_json
                }
            )

        # Add timestamp to parsed data (ISO 8601 format)
        extraction_timestamp = pd.Timestamp.now(tz='UTC').isoformat()
        if isinstance(parsed_data, dict):
            parsed_data["timestamp"] = extraction_timestamp

        # Process and validate data
        validation_errors = []
        warnings = []

        # Enforce category requirement - NEVER allow null
        if isinstance(parsed_data, dict):
            category = parsed_data.get("category")
            if not category or category is None or (isinstance(category, str) and category.strip() == ""):
                parsed_data["category"] = "OTHER"
                warnings.append("Category was not provided by OCR, defaulted to 'OTHER'")

        # Basic validation for required fields
        if isinstance(parsed_data, dict):
            # Validate category (must never be null after enforcement)
            category = parsed_data.get("category")
            if not category or category is None:
                validation_errors.append("Category is required and cannot be null")

            # Validate merchant_name
            if not parsed_data.get("merchant_name"):
                warnings.append("Merchant name not found or unclear in the receipt")

            # Validate total_amount
            total_amount = parsed_data.get("total_amount")
            if total_amount is not None:
                try:
                    float(total_amount)
                except (ValueError, TypeError):
                    validation_errors.append("Total amount is not a valid number")

            # Validate items array
            items = parsed_data.get("items", [])
            if not items:
                warnings.append("No line items found in the receipt")
            else:
                for i, item in enumerate(items):
                    if not isinstance(item, dict):
                        validation_errors.append(f"Item {i+1} is not properly formatted")
                        continue

                    # Validate item fields
                    if not item.get("item_name"):
                        validation_errors.append(f"Item {i+1} is missing item name/description")

                    # Validate item_price
                    item_price = item.get("item_price")
                    if item_price is not None:
                        try:
                            float(item_price)
                        except (ValueError, TypeError):
                            validation_errors.append(f"Item {i+1} has invalid price format")

                    # Validate quantity
                    quantity = item.get("quantity")
                    if quantity is not None:
                        try:
                            float(quantity)
                        except (ValueError, TypeError):
                            validation_errors.append(f"Item {i+1} has invalid quantity format")

        # Store processed data in memory for potential re-access
        upload_time = pd.Timestamp.now().isoformat()
        uploaded_images[image_id] = {
            "file_path": temp_file_path,
            "filename": file.filename,
            "content_type": file.content_type,
            "upload_time": upload_time,
            "extracted_data": parsed_data,
            "warnings": warnings,
            "validation_errors": validation_errors,
            "processed": True
        }

        # Prepare response data
        response_data = {
            "success": True,
            "image_id": image_id,
            "filename": file.filename,
            "extracted_data": parsed_data,
            "warnings": warnings,
            "validation_errors": validation_errors,
            "processing_info": {
                "image_processed": True,
                "data_extracted": True,
                "data_validated": len(validation_errors) == 0,
                "upload_time": upload_time
            },
            "message": "Image uploaded and processed successfully."
        }

        # Check if there are critical validation errors
        if validation_errors:
            response_data["success"] = False
            response_data["error"] = "Data validation failed"

        return JSONResponse(content=response_data)

    except Exception as e:
        # Clean up temporary file on error
        try:
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        except:
            pass

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Failed to process image: {str(e)}"
            }
        )

@router.get("/extract-data")
async def extract_data():
    """
    Retrieve OCR data from the most recently uploaded and processed image

    Returns:
        JSON response with extracted and processed data from the most recent upload
    """

    # Check if any images have been uploaded
    if not uploaded_images:
        raise HTTPException(
            status_code=404,
            detail="No images found. Please upload an image first."
        )

    # Find the most recently uploaded image
    most_recent_image_id = max(uploaded_images.keys(),
                              key=lambda img_id: uploaded_images[img_id]["upload_time"])

    image_id = most_recent_image_id

    image_info = uploaded_images[image_id]

    try:
        # If data was already processed during upload, return cached results
        if image_info.get("processed", False):
            response_data = {
                "success": True,
                "image_id": image_id,
                "filename": image_info.get("filename"),
                "extracted_data": image_info.get("extracted_data"),
                "warnings": image_info.get("warnings", []),
                "validation_errors": image_info.get("validation_errors", []),
                "processing_info": {
                    "image_processed": True,
                    "data_extracted": True,
                    "data_validated": len(image_info.get("validation_errors", [])) == 0,
                    "upload_time": image_info["upload_time"],
                    "cached_result": True
                },
                "message": "Returning cached OCR data from upload processing."
            }

            # Check if there are critical validation errors
            if image_info.get("validation_errors"):
                response_data["success"] = False
                response_data["error"] = "Data validation failed"

            return JSONResponse(content=response_data)

        # If not processed yet (fallback for old uploads), process now
        # Load image from temporary file
        if not os.path.exists(image_info["file_path"]):
            raise HTTPException(
                status_code=404,
                detail="Image file not found. It may have been already processed or expired."
            )

        image = Image.open(image_info["file_path"])

        # Extract data using Gemini API
        extracted_json = process_image_with_gemini(image)

        # Clean and parse JSON
        cleaned_json = clean_json_string(extracted_json)

        if not cleaned_json.strip():
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Extracted data appears to be empty after cleaning",
                    "original_data": extracted_json,
                    "cleaned_data": cleaned_json
                }
            )

        # Parse JSON data
        try:
            parsed_data = json.loads(cleaned_json)
        except json.JSONDecodeError as e:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": f"Invalid JSON format: {str(e)}",
                    "original_data": extracted_json,
                    "cleaned_data": cleaned_json
                }
            )

        # Add timestamp to parsed data (ISO 8601 format)
        extraction_timestamp = pd.Timestamp.now(tz='UTC').isoformat()
        if isinstance(parsed_data, dict):
            parsed_data["timestamp"] = extraction_timestamp

        # Process data validation (same logic as upload endpoint)
        validation_errors = []
        warnings = []

        # Enforce category requirement - NEVER allow null
        if isinstance(parsed_data, dict):
            category = parsed_data.get("category")
            if not category or category is None or (isinstance(category, str) and category.strip() == ""):
                parsed_data["category"] = "OTHER"
                warnings.append("Category was not provided by OCR, defaulted to 'OTHER'")

        # Basic validation for required fields
        if isinstance(parsed_data, dict):
            # Validate category (must never be null after enforcement)
            category = parsed_data.get("category")
            if not category or category is None:
                validation_errors.append("Category is required and cannot be null")

            # Validate merchant_name
            if not parsed_data.get("merchant_name"):
                warnings.append("Merchant name not found or unclear in the receipt")

            # Validate total_amount
            total_amount = parsed_data.get("total_amount")
            if total_amount is not None:
                try:
                    float(total_amount)
                except (ValueError, TypeError):
                    validation_errors.append("Total amount is not a valid number")

            # Validate items array
            items = parsed_data.get("items", [])
            if not items:
                warnings.append("No line items found in the receipt")
            else:
                for i, item in enumerate(items):
                    if not isinstance(item, dict):
                        validation_errors.append(f"Item {i+1} is not properly formatted")
                        continue

                    # Validate item fields
                    if not item.get("item_name"):
                        validation_errors.append(f"Item {i+1} is missing item name/description")

                    # Validate item_price
                    item_price = item.get("item_price")
                    if item_price is not None:
                        try:
                            float(item_price)
                        except (ValueError, TypeError):
                            validation_errors.append(f"Item {i+1} has invalid price format")

                    # Validate quantity
                    quantity = item.get("quantity")
                    if quantity is not None:
                        try:
                            float(quantity)
                        except (ValueError, TypeError):
                            validation_errors.append(f"Item {i+1} has invalid quantity format")

        # Prepare response data
        response_data = {
            "success": True,
            "image_id": image_id,
            "filename": image_info.get("filename"),
            "extracted_data": parsed_data,
            "warnings": warnings,
            "validation_errors": validation_errors,
            "processing_info": {
                "image_processed": True,
                "data_extracted": True,
                "data_validated": len(validation_errors) == 0,
                "upload_time": image_info["upload_time"],
                "cached_result": False
            },
            "message": "Image re-processed successfully."
        }

        # Check if there are critical validation errors
        if validation_errors:
            response_data["success"] = False
            response_data["error"] = "Data validation failed"

        # Clean up: Remove the temporary file and memory entry
        try:
            os.remove(image_info["file_path"])
            del uploaded_images[image_id]
        except Exception as cleanup_error:
            # Log cleanup error but don't fail the response
            response_data["cleanup_warning"] = f"Failed to clean up temporary file: {str(cleanup_error)}"

        return JSONResponse(content=response_data)

    except Exception as e:
        # Clean up on error
        try:
            if os.path.exists(image_info["file_path"]):
                os.remove(image_info["file_path"])
            del uploaded_images[image_id]
        except:
            pass

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Unexpected error during processing: {str(e)}"
            }
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8050))
    uvicorn.run(app, host="0.0.0.0", port=port)
