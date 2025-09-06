from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import os, json, logging
from datetime import datetime
from ..routes.reminders import book_appointment, send_reminder

router = APIRouter()

# ----------------------------
# Logging Setup
# ----------------------------
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "access.log")),
        logging.FileHandler(os.path.join(LOG_DIR, "error.log")),
        logging.FileHandler(os.path.join(LOG_DIR, "warning.log")),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# ----------------------------
# Paths
# ----------------------------
PATIENTS_FOLDER = os.path.join("apps", "data", "patients")
os.makedirs(PATIENTS_FOLDER, exist_ok=True)

# ----------------------------
# Pydantic Model
# ----------------------------
class PatientModel(BaseModel):
    patient_id: str
    name: str
    dob: str
    gender: str
    phone: str
    email: EmailStr
    address: str
    insurance: Optional[dict] = None

def patient_file_path(patient_id: str) -> str:
    return os.path.join(PATIENTS_FOLDER, f"patient_{patient_id}.json")

def patient_exists(patient_id: str) -> bool:
    return os.path.exists(patient_file_path(patient_id))

# ----------------------------
# GET - List all patients
# ----------------------------
@router.get("/", response_model=List[PatientModel])
async def list_patients():
    try:
        patients = []
        for filename in os.listdir(PATIENTS_FOLDER):
            if filename.endswith(".json"):
                with open(os.path.join(PATIENTS_FOLDER, filename), "r", encoding="utf-8") as f:
                    patients.append(json.load(f))

        logger.info(f"Retrieved {len(patients)} patient records successfully")
        return patients

    except Exception as e:
        logger.error(f"Error retrieving patients: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving patients")

# ----------------------------
# POST - Create Patient
# ----------------------------
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=PatientModel)
async def create_patient(patient: PatientModel):
    # Check if patient already exists
    if patient_exists(patient.patient_id):
        logger.warning(f"Attempt to create patient failed: ID {patient.patient_id} already exists")
        raise HTTPException(status_code=400, detail="Patient ID already exists")

    try:
        # Save patient data to JSON
        with open(patient_file_path(patient.patient_id), "w", encoding="utf-8") as f:
            json.dump(patient.dict(), f, indent=4, ensure_ascii=False)

        logger.info(f"Patient {patient.patient_id} created and stored successfully")

        # Auto-book appointment
        appointment = book_appointment(patient.patient_id)
        logger.info(f"Appointment booked for patient {patient.patient_id}: {appointment}")

        # Send 3 reminders
        for i in range(3):
            send_reminder(appointment, patient.email)
            logger.info(f"Reminder {i+1}/3 sent to {patient.email} for appointment {appointment}")

        return patient

    except Exception as e:
        logger.error(f"Error creating patient {patient.patient_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating patient")
