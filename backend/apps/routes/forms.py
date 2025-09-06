from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
import os, shutil, json

router = APIRouter()

# ----------------------------
# Paths
# ----------------------------
UPLOADED_FOLDER = os.path.join("apps", "forms", "uploaded")
PROCESSED_FOLDER = os.path.join("apps", "forms", "processed")
METADATA_FOLDER = os.path.join("apps", "data", "forms")

os.makedirs(UPLOADED_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs(METADATA_FOLDER, exist_ok=True)

# ----------------------------
# Pydantic Model for Form Metadata
# ----------------------------
class FormMetadata(BaseModel):
    form_id: str = Field(..., example="FORM001")
    patient_id: str = Field(..., example="001")
    file_name: str = Field(..., example="form_001.pdf")
    upload_date: str = Field(..., example="2025-01-01")
    processed: bool = Field(default=False)
    notes: str = Field(default="", example="Initial upload")

# ----------------------------
# Utility Functions
# ----------------------------
def metadata_file_path(form_id: str) -> str:
    return os.path.join(METADATA_FOLDER, f"{form_id}.json")

def form_exists(form_id: str) -> bool:
    return os.path.exists(metadata_file_path(form_id))

# ----------------------------
# API Endpoints
# ----------------------------
@router.get("/", response_model=List[FormMetadata])
async def list_forms():
    """
    List all uploaded form metadata
    """
    try:
        forms = []
        for filename in os.listdir(METADATA_FOLDER):
            if filename.endswith(".json"):
                with open(os.path.join(METADATA_FOLDER, filename), "r", encoding="utf-8") as f:
                    forms.append(json.load(f))
        return forms
    except Exception:
        raise HTTPException(status_code=500, detail="Error reading forms metadata")

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_form(patient_id: str, file: UploadFile = File(...)):
    """
    Upload a PDF form and store metadata as JSON.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    form_id = f"FORM{len(os.listdir(METADATA_FOLDER)) + 1:03d}"
    upload_path = os.path.join(UPLOADED_FOLDER, file.filename)

    try:
        # Save uploaded PDF
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Save metadata with correct date
        metadata = FormMetadata(
            form_id=form_id,
            patient_id=patient_id,
            file_name=file.filename,
            upload_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            processed=False,
            notes="Initial upload"
        )
        with open(metadata_file_path(form_id), "w", encoding="utf-8") as f:
            json.dump(metadata.dict(), f, indent=4, ensure_ascii=False)

        return metadata

    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
