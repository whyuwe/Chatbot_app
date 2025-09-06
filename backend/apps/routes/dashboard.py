from fastapi import APIRouter, HTTPException, Query
import os, json, logging
from datetime import datetime
from typing import Optional

router = APIRouter()

# ----------------------------
# Logging configuration
# ----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("dashboard.log"),
        logging.StreamHandler()
    ]
)

# ----------------------------
# Paths to data folders
# ----------------------------
PATIENTS_FOLDER = os.path.join("apps", "data", "patients")
APPOINTMENTS_FOLDER = os.path.join("apps", "data", "appointments")
FORMS_FOLDER = os.path.join("apps", "data", "forms")

# ----------------------------
# Utility Functions
# ----------------------------
def read_all_json(folder_path: str):
    """Read all JSON files from a folder"""
    if not os.path.exists(folder_path):
        return []
    data = []
    for file in os.listdir(folder_path):
        if file.endswith(".json"):
            try:
                with open(os.path.join(folder_path, file), "r", encoding="utf-8") as f:
                    data.append(json.load(f))
            except Exception as e:
                logging.warning(f"Failed to read file {file}: {e}")
    return data

# ----------------------------
# API Endpoint
# ----------------------------
@router.get("/", summary="Get dashboard statistics with optional filters")
async def get_dashboard_stats(
    search: Optional[str] = Query(None, description="Search by name or patient ID"),
    insurance: Optional[str] = Query(None, description="Filter by insurance name")
):
    try:
        # Read data
        patients = read_all_json(PATIENTS_FOLDER)
        appointments = read_all_json(APPOINTMENTS_FOLDER)
        forms = read_all_json(FORMS_FOLDER)

        # Apply filters
        if search:
            search_lower = search.lower()
            patients = [
                p for p in patients
                if search_lower in p.get("name", "").lower()
                or search_lower in p.get("patient_id", "").lower()
            ]

        if insurance:
            insurance_lower = insurance.lower()
            patients = [
                p for p in patients
                if insurance_lower in p.get("insurance", "").lower()
            ]

        # Related appointments for filtered patients
        patient_ids = {p.get("patient_id") for p in patients}
        appointments = [a for a in appointments if a.get("patient_id") in patient_ids]

        # Forms related to filtered patients
        forms = [f for f in forms if f.get("patient_id") in patient_ids]

        # Stats
        total_patients = len(patients)
        total_appointments = len(appointments)
        upcoming_appointments = len([a for a in appointments if a.get("status") == "upcoming"])
        completed_appointments = len([a for a in appointments if a.get("status") == "completed"])
        total_forms = len(forms)
        processed_forms = len([f for f in forms if f.get("processed")])
        unprocessed_forms = total_forms - processed_forms

        # Age distribution
        age_distribution = {}
        for p in patients:
            try:
                dob = datetime.strptime(p.get("dob", "2000-01-01"), "%Y-%m-%d")
                age = (datetime.today() - dob).days // 365
                age_group = f"{(age // 10) * 10}-{(age // 10) * 10 + 9}"
                age_distribution[age_group] = age_distribution.get(age_group, 0) + 1
            except Exception as e:
                logging.warning(f"Failed to calculate age for patient {p.get('patient_id', 'unknown')}: {e}")

        # Appointments per patient
        appointments_per_patient = {}
        for a in appointments:
            pid = a.get("patient_id", "unknown")
            appointments_per_patient[pid] = appointments_per_patient.get(pid, 0) + 1

        dashboard_data = {
            "total_patients": total_patients,
            "total_appointments": total_appointments,
            "upcoming_appointments": upcoming_appointments,
            "completed_appointments": completed_appointments,
            "total_forms": total_forms,
            "processed_forms": processed_forms,
            "unprocessed_forms": unprocessed_forms,
            "age_distribution": age_distribution,
            "appointments_per_patient": appointments_per_patient,
            "patients": patients  # for table view in frontend
        }

        logging.info("Dashboard data retrieved successfully")
        return dashboard_data

    except Exception as e:
        logging.error(f"Error in dashboard API: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
