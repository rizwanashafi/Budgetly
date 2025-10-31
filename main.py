from fastapi import FastAPI
from OCR.api import router as ocr_router
from ai_insights.api import router as ai_insights_router

app = FastAPI(
    title="OCR and AI insights",
    description="Simple OCR API - upload images and get extracted data automatically. Also, analyze budget data using AI insights.",
    version="5.0.0"
)

app.include_router(ocr_router)
app.include_router(ai_insights_router)

@app.get("/")
def root():
    return {"message": "Main FastAPI running"}