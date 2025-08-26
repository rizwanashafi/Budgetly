#!/usr/bin/env python3
"""
Utility functions for the OCR FastAPI application
"""

import re

def clean_json_string(json_string):
    """
    Clean Gemini's Markdown-style JSON response to extract pure JSON
    
    Args:
        json_string: Raw response from Gemini API that may contain markdown formatting
        
    Returns:
        Cleaned JSON string
    """
    # First try to extract JSON from markdown code blocks
    json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    match = re.search(json_pattern, json_string, re.DOTALL)
    if match:
        return match.group(1).strip()

    # If no code blocks, try to find JSON object directly
    json_pattern = r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})'
    match = re.search(json_pattern, json_string, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Fallback: remove markdown code blocks with any number of backticks
    cleaned = re.sub(r"`+(?:json)?\s*", "", json_string)
    # Remove trailing backticks and whitespace
    cleaned = re.sub(r"\s*`+\s*$", "", cleaned)
    # Strip any remaining whitespace
    cleaned = cleaned.strip()
    return cleaned
