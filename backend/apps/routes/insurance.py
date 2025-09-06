import os
import json
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from datetime import datetime

# ----------------------------
# Logging configuration
# ----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/insurance.log"),  # Logs stored in logs folder
        logging.StreamHandler()  # Also print to console
    ]
)

router = APIRouter()

# ----------------------------
# Paths
# ----------------------------
INSURANCE_FOLDER = os.path.join("apps", "data", "insurance")
os.makedirs(INSURANCE_FOLDER, exist_ok=True)
os.makedirs("logs", exist_ok=True)  # Ensure logs directory exists

# ----------------------------
# Pydantic Model
# ----------------------------
class InsuranceModel(BaseModel):
    insurance_id: str = Field(..., example="INS001")
    patient_id: str = Field(..., example="001")
    carrier: str = Field(..., example="MediCare")
    member_id: str = Field(..., example="AB12345")
    group_no: Optional[str] = Field(None, example="GRP1001")
    valid_until: Optional[str] = Field(None, pattern=r"\d{4}-\d{2}-\d{2}", example="2025-12-31")
    notes: Optional[str] = Field(None, example="Primary insurance plan")

# ----------------------------
# Utility functions
# ----------------------------
def insurance_file_path(insurance_id: str) -> str:
    return os.path.join(INSURANCE_FOLDER, f"insurance_{insurance_id}.json")

def insurance_exists(insurance_id: str) -> bool:
    return os.path.exists(insurance_file_path(insurance_id))

# ----------------------------
# GET - All Insurance
# ----------------------------
@router.get("/", response_model=List[InsuranceModel])
async def get_all_insurances():
    try:
        records = []
        for filename in os.listdir(INSURANCE_FOLDER):
            if filename.endswith(".json"):
                with open(os.path.join(INSURANCE_FOLDER, filename), "r", encoding="utf-8") as f:
                    records.append(json.load(f))
        logging.info(f"Fetched {len(records)} insurance records")
        return records
    except Exception as e:
        logging.error(f"Error fetching insurance records: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching insurance records")

# ----------------------------
# GET - Single Insurance
# ----------------------------
@router.get("/{insurance_id}", response_model=InsuranceModel)
async def get_insurance(insurance_id: str):
    if not insurance_exists(insurance_id):
        logging.warning(f"Insurance {insurance_id} not found")
        raise HTTPException(status_code=404, detail="Insurance record not found")
    try:
        with open(insurance_file_path(insurance_id), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error reading insurance {insurance_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error reading insurance data")

# ----------------------------
# POST - Create Insurance
# ----------------------------
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=InsuranceModel)
async def create_insurance(insurance: InsuranceModel):
    if insurance_exists(insurance.insurance_id):
        logging.warning(f"Insurance {insurance.insurance_id} already exists")
        raise HTTPException(status_code=400, detail="Insurance ID already exists")
    try:
        with open(insurance_file_path(insurance.insurance_id), "w", encoding="utf-8") as f:
            json.dump(insurance.dict(), f, indent=4, ensure_ascii=False)
        logging.info(f"Insurance {insurance.insurance_id} created successfully")
        return insurance
    except Exception as e:
        logging.error(f"Error creating insurance {insurance.insurance_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating insurance record")

# ----------------------------
# PUT - Update Insurance
# ----------------------------
@router.put("/{insurance_id}", response_model=InsuranceModel)
async def update_insurance(insurance_id: str, insurance: InsuranceModel):
    if not insurance_exists(insurance_id):
        logging.warning(f"Insurance {insurance_id} not found for update")
        raise HTTPException(status_code=404, detail="Insurance record not found")
    try:
        with open(insurance_file_path(insurance_id), "w", encoding="utf-8") as f:
            json.dump(insurance.dict(), f, indent=4, ensure_ascii=False)
        logging.info(f"Insurance {insurance_id} updated successfully")
        return insurance
    except Exception as e:
        logging.error(f"Error updating insurance {insurance_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error updating insurance record")

# ----------------------------
# DELETE - Remove Insurance
# ----------------------------
@router.delete("/{insurance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_insurance(insurance_id: str):
    if not insurance_exists(insurance_id):
        logging.warning(f"Insurance {insurance_id} not found for deletion")
        raise HTTPException(status_code=404, detail="Insurance record not found")
    try:
        os.remove(insurance_file_path(insurance_id))
        logging.info(f"Insurance {insurance_id} deleted successfully")
        return {"message": "Insurance record deleted successfully"}
    except Exception as e:
        logging.error(f"Error deleting insurance {insurance_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error deleting insurance record")

# ----------------------------
# GET - Search Insurance
# ----------------------------
@router.get("/insurance/search")
async def search_insurance(
    name: Optional[str] = None,
    insurance_type: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: Optional[str] = None
):
    try:
        results = []

        for file in os.listdir(INSURANCE_FOLDER):
            if file.endswith(".json"):
                with open(os.path.join(INSURANCE_FOLDER, file), "r", encoding="utf-8") as f:
                    data = json.load(f)

                    if name and name.lower() not in data.get("carrier", "").lower():
                        continue
                    if insurance_type and insurance_type.lower() != data.get("notes", "").lower():
                        continue
                    if status and status.lower() != data.get("valid_until", "").lower():
                        continue

                    results.append(data)

        if sort_by:
            results.sort(key=lambda x: x.get(sort_by, ""), reverse=False)

        logging.info(f"Search found {len(results)} insurance records")
        return {"count": len(results), "results": results}
    except Exception as e:
        logging.error(f"Error searching insurance records: {str(e)}")
        raise HTTPException(status_code=500, detail="Error searching insurance records")
