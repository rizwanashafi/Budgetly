# OCR Image Processing API

A universal two-step FastAPI REST API that processes receipt images using Google's Gemini AI to extract standardized structured data. Upload images first, then extract OCR data in a separate step.

## Features

- **Two-Step Processing**: Upload images and extract data in separate API calls
- **Universal Receipt Processing**: Works with all receipt types without manual category selection
- **Standardized Data Extraction**: Consistent merchant name and item-level data extraction
- **Detailed Item Extraction**: Extracts quantity, item name, and price for each line item
- **Image Upload**: Support for PNG, JPG, and JPEG formats via multipart form data
- **AI-Powered OCR**: Uses Gemini 2.0 Flash model for text extraction and data structuring
- **Data Validation**: Comprehensive validation of extracted data
- **Temporary Storage**: Images stored temporarily only during processing
- **Automatic Cleanup**: Images removed after data extraction
- **Enhanced Error Handling**: Robust error handling and validation
- --------------

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file with your Gemini API key:

```env
# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key
```

### 3. Run the FastAPI Application

```bash
uvicorn fastapi_app:app --reload
```

The API will be available at: `http://localhost:8000`

## Standardized Data Format

The API extracts receipt data in a consistent format regardless of receipt type:

```json
{
  "merchant_name": "Business name (store, restaurant, pharmacy, etc.)",
  "transaction_date": "Date in YYYY-MM-DD format",
  "total_amount": "Total amount as number",
  "tax": "Tax amount as number",
  "items": [
    {
      "quantity": "Number of items (defaults to 1 if not specified)",
      "item_name": "Item name/description",
      "item_price": "Price for this line item as number"
    }
  ]
}
```

**Key Features:**
- **Universal Processing**: Works with all receipt types without category selection
- **Detailed Item Extraction**: Captures quantity, name, and price for each line item
- **Standardized Merchant Info**: Consistent merchant_name field across all receipt types
- **Comprehensive Coverage**: Extracts all visible line items from the receipt

## API Endpoints

### POST /upload-image
Upload an image file for universal receipt processing.

**Request:**
- `file`: Image file (PNG, JPG, JPEG) as multipart form data

**Response:**
```json
{
  "success": true,
  "image_id": "uuid-string",
  "filename": "receipt.jpg",
  "message": "Image uploaded successfully. Use the image_id to extract data."
}
```

### GET /extract-data/{image_id}
Extract and return OCR data from a previously uploaded image.

**Request:**
- `image_id`: Image ID returned from upload endpoint (path parameter)

**Response:**
```json
{
  "success": true,
  "image_id": "uuid-string",
  "extracted_data": {
    "merchant_name": "7-ELEVEN",
    "transaction_date": "2021-05-07",
    "total_amount": 14.00,
    "tax": 1.27,
    "items": [
      {
        "quantity": 1,
        "item_name": "AZ Sweet TEA 23ZCH",
        "item_price": 1.008
      },
      {
        "quantity": 2,
        "item_name": "5 Hr EnergyXS 1.93Z",
        "item_price": 1.80
      },
      {
        "quantity": 1,
        "item_name": "PROMOTION 5 Hr EnergyXS 1.93Z",
        "item_price": -1.007
      }
    ]
  },
  "warnings": [],
  "validation_errors": [],
  "processing_info": {
    "image_processed": true,
    "data_extracted": true,
    "data_validated": true,
    "upload_time": "2024-01-01T12:00:00"
  }
}
```

## How to Use

### Step 1: Upload Image
```bash
curl -X POST "http://localhost:8000/upload-image" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@receipt.jpg"
```

### Step 2: Extract Data
```bash
curl -X GET "http://localhost:8000/extract-data/{image_id}"
```

### Using Python requests:
```python
import requests

# Step 1: Upload image
with open('receipt.jpg', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/upload-image', files=files)
    upload_result = response.json()
    image_id = upload_result['image_id']

# Step 2: Extract data
response = requests.get(f'http://localhost:8000/extract-data/{image_id}')
result = response.json()
print(result['extracted_data'])
```

## Error Handling

The application includes comprehensive error handling for:
- Gemini API errors
- JSON parsing problems
- File upload validation
- Image processing failures
- Temporary file management

## Security Features

- Environment variable configuration for sensitive data
- Input validation for uploaded files
- Automatic cleanup of temporary files
- Secure image processing

## Cloud Deployment

This application is optimized for cloud deployment with:
- Minimal dependencies
- Stateless architecture
- Temporary file handling
- Environment-based configuration

## Troubleshooting

### Gemini API Issues
- Verify your `GEMINI_API_KEY` in the `.env` file
- Check your Google Cloud API quota and billing
- Ensure the Gemini API is enabled in your Google Cloud project

### Image Processing Issues
- Supported formats: PNG, JPG, JPEG
- Ensure images contain readable text
- Try different image qualities if extraction fails

## Support

For issues or questions, check:
1. API response status and error messages
2. Console logs for detailed error information
3. Gemini API quota and billing status
