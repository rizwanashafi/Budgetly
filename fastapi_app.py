#!/usr/bin/env python3
"""
FastAPI OCR Application - Two-Step Image Processing API
Upload images and extract OCR data in separate steps
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Path
from fastapi.responses import JSONResponse
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image
import pandas as pd
from app_utils import clean_json_string
import json
import os
import uuid
import tempfile
from typing import Dict

# Load environment variables
load_dotenv()

# Removed CategoryEnum - using universal receipt processing

# Initialize FastAPI app
app = FastAPI(
    title="OCR Image Processing API",
    description="Two-step API for uploading images and extracting OCR data",
    version="4.0.0"
)

# In-memory storage for uploaded images and their metadata
uploaded_images: Dict[str, Dict] = {}

# Configure Gemini API
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY environment variable is required")

genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel('gemini-2.0-flash')

def get_gemini_prompt():
    """Get the Gemini AI prompt for universal receipt OCR processing"""
    return """You are an OCR assistant that extracts structured data from receipt images. Extract the following information in a standardized JSON format regardless of receipt type:

{
  "merchant_name": "store/restaurant/pharmacy name or null",
#   "merchant_contact": "phone number or contact info or null",
  "transaction_date": "date in YYYY-MM-DD format or null",
  "total_amount": "total amount as number or null",
  "tax": "tax amount as number or null",
  "items": [
    {
      "quantity": "number of items purchased (as number) or 1 if not specified",
      "item_name": "item name/description",
      "item_price": "price per individual item or total price for this line item (as number)"
    }
  ]
}

Instructions:
- Extract merchant_name from any business name visible on the receipt (restaurant, store, pharmacy, etc.)
- For items array, include ALL line items visible on the receipt
- If quantity is not explicitly shown, use 1 as default
- For item_price, extract the price shown for that specific line item
- Use null for any field where information is missing, unclear, or not visible
- Ensure all prices are extracted as numbers (not strings)
- Include as many items as are visible on the receipt

Important: Only extract information that is clearly visible and readable in the receipt image. Focus on accuracy over completeness."""

def process_image_with_gemini(image: Image.Image) -> str:
    """Process image with Gemini API to extract structured JSON"""
    prompt = get_gemini_prompt()
    response = model.generate_content([prompt, image])
    return response.text

def validate_image_file(file: UploadFile) -> bool:
    """Validate uploaded image file"""
    allowed_types = ["image/png", "image/jpeg", "image/jpg"]
    return file.content_type in allowed_types


@app.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...)
):
    """
    Upload an image file for OCR processing

    Args:
        file: Image file (PNG, JPG, JPEG)

    Returns:
        JSON response with upload confirmation and image ID
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

        # Read image data
        image_data = await file.read()

        # Create temporary file to store the image
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, f"ocr_image_{image_id}.jpg")

        # Save image to temporary file
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(image_data)

        # Store image metadata in memory
        uploaded_images[image_id] = {
            "file_path": temp_file_path,
            "filename": file.filename,
            "content_type": file.content_type,
            "upload_time": pd.Timestamp.now().isoformat()
        }

        return JSONResponse(content={
            "success": True,
            "image_id": image_id,
            "filename": file.filename,
            "message": "Image uploaded successfully. Use the image_id to extract data."
        })

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Failed to upload image: {str(e)}"
            }
        )

@app.get("/extract-data/{image_id}")
async def extract_data(image_id: str = Path(..., description="Image ID from upload")):
    """
    Extract and return OCR data from a previously uploaded image

    Args:
        image_id: Image ID returned from upload endpoint

    Returns:
        JSON response with extracted and processed data
    """

    # Check if image exists
    if image_id not in uploaded_images:
        raise HTTPException(
            status_code=404,
            detail="Image not found. Please upload an image first."
        )

    image_info = uploaded_images[image_id]

    try:
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

        # Process data in a generic way without category-specific transformations
        validation_errors = []
        warnings = []

        # Basic validation for required fields
        if isinstance(parsed_data, dict):
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
            "extracted_data": parsed_data,
            "warnings": warnings,
            "validation_errors": validation_errors,
            "processing_info": {
                "image_processed": True,
                "data_extracted": True,
                "data_validated": len(validation_errors) == 0,
                "upload_time": image_info["upload_time"]
            }
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
