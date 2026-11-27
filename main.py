from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from OCR.api import router as ocr_router
from ai_insights.api import router as ai_insights_router
from notification.main import router as notification_router
from fastapi.responses import RedirectResponse


app = FastAPI(
    title="OCR, AI insights and notificationAPI",
    description="Simple OCR API - upload images and get extracted data automatically. Also, analyze budget data using AI insights.",
    version="5.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ocr_router)
app.include_router(ai_insights_router)
app.include_router(notification_router)

# @app.get("/")
# def root():
#     return {"message": "Main FastAPI running"}
@app.get("/", include_in_schema=False)
async def root():
    """
    Redirect the root URL to the interactive Swagger docs.
    """
    return RedirectResponse(url="/docs")