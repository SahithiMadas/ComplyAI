"""Utility functions for the ComplyAI application."""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

def ensure_directories():
    """Create necessary directories if they don't exist."""
    directories = [
        "uploaded_pdfs",
        "chroma_db",
        "outputs/reports",
        "outputs/visuals",
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def load_compliance_standard(standard_name: str) -> List[Dict[str, Any]]:
    """Load a compliance standard from JSON file.
    
    Args:
        standard_name: Name of the standard (e.g., 'iso_27001', 'nist')
        
    Returns:
        List of controls for the specified standard
    """
    standard_file = Path(f"compliance_db/{standard_name}.json")
    
    if not standard_file.exists():
        raise FileNotFoundError(f"Compliance standard file not found: {standard_file}")
    
    with open(standard_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_available_standards() -> List[str]:
    """Get a list of available compliance standards.
    
    Returns:
        List of available standards (without .json extension)
    """
    standards_dir = Path("compliance_db")
    
    if not standards_dir.exists():
        return []
    
    return [f.stem for f in standards_dir.glob("*.json")]

def save_report(report_data, filename: str = "gap_matrix.csv"):
    """Save a report to the outputs/reports directory.
    
    Args:
        report_data: Data to save (DataFrame for CSV)
        filename: Name of the report file
    """
    output_dir = Path("outputs/reports")
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = output_dir / filename
    report_data.to_csv(output_path, index=False)
    return output_path