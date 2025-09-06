"""
Appointments API
Handles CRUD operations for appointment data with validation,
error handling, logging, JSON storage, email reminders, and filtering.
"""

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import Optional, List
import os, json
from datetime import datetime
import logging

# Assuming these imports exist in your project
from ..routes.reminders import schedule_reminders
from ..routes.patients import patient_file_path, patient_exists

router = APIRouter()

# ----------------------------
# Logging configuration
# ----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("appointments.log"),
        logging.StreamHandler()
    ]
)

# ----------------------------
# Paths
# ----------------------------
APPOINTMENTS_FOLDER = os.path.join("apps", "data", "appointments")
os.makedirs(APPOINTMENTS_FOLDER, exist_ok=True)

# ----------------------------
# Pydantic Model for Appointments
# ----------------------------
class AppointmentModel(BaseModel):
    appointment_id: str = Field(..., example="A001")
    patient_id: str = Field(..., example="001")
    date: str = Field(..., pattern=r"\d{4}-\d{2}-\d{2}", example="2025-09-06")
    slot: str = Field(..., pattern=r"^\d{2}:\d{2}-\d{2}:\d{2}$", example="09:00-09:30")
    status: str = Field(..., pattern=r"^(upcoming|completed|cancelled)$", example="upcoming")
    notes: Optional[str] = Field(None, example="Patient requested morning slot")
    reminders_sent: Optional[List[str]] = Field(default_factory=list)

# ----------------------------
# Utility functions
# ----------------------------
def appointment_file_path(appointment_id: str) -> str:
    return os.path.join(APPOINTMENTS_FOLDER, f"appointment_{appointment_id}.json")

def appointment_exists(appointment_id: str) -> bool:
    return os.path.exists(appointment_file_path(appointment_id))

def read_json(folder: str) -> List[dict]:
    result = []
    for f in os.listdir(folder):
        if f.endswith('.json'):
            try:
                with open(os.path.join(folder, f), 'r', encoding='utf-8') as file:
                    result.append(json.load(file))
            except Exception as e:
                logging.error(f"Failed to read {f}: {e}")
    return result

# ----------------------------
# GET all appointments with filters
# ----------------------------
@router.get("/", response_model=List[AppointmentModel])
async def get_appointments_filtered(
    patient_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None, regex="^(upcoming|completed|cancelled)$"),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    try:
        data = read_json(APPOINTMENTS_FOLDER)
        if patient_id:
            data = [d for d in data if d["patient_id"] == patient_id]
        if status:
            data = [d for d in data if d["status"] == status]
        if date_from:
            data = [d for d in data if d["date"] >= date_from]
        if date_to:
            data = [d for d in data if d["date"] <= date_to]

        logging.info(f"Fetched {len(data)} appointments with filters")
        return data
    except Exception as e:
        logging.error(f"Error fetching appointments: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching appointments")

# ----------------------------
# CRUD Endpoints
# ----------------------------
@router.get("/{appointment_id}", response_model=AppointmentModel)
async def get_appointment(appointment_id: str):
    if not appointment_exists(appointment_id):
        logging.warning(f"Appointment {appointment_id} not found")
        raise HTTPException(status_code=404, detail="Appointment not found")
    try:
        with open(appointment_file_path(appointment_id), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error reading appointment {appointment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error reading appointment data")

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=AppointmentModel)
async def create_appointment(appointment: AppointmentModel):
    if appointment_exists(appointment.appointment_id):
        raise HTTPException(status_code=400, detail="Appointment ID already exists")
    try:
        with open(appointment_file_path(appointment.appointment_id), "w", encoding="utf-8") as f:
            json.dump(appointment.dict(), f, indent=4, ensure_ascii=False)

        # Schedule reminder if patient exists
        if patient_exists(appointment.patient_id):
            with open(patient_file_path(appointment.patient_id), "r", encoding="utf-8") as pf:
                patient_data = json.load(pf)
                schedule_reminders(appointment.dict(), patient_data.get("email"))

        logging.info(f"Created appointment {appointment.appointment_id} for patient {appointment.patient_id}")
        return appointment
    except Exception as e:
        logging.error(f"Error creating appointment {appointment.appointment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating appointment")

@router.put("/{appointment_id}", response_model=AppointmentModel)
async def update_appointment(appointment_id: str, appointment: AppointmentModel):
    if not appointment_exists(appointment_id):
        raise HTTPException(status_code=404, detail="Appointment not found")
    try:
        with open(appointment_file_path(appointment_id), "w", encoding="utf-8") as f:
            json.dump(appointment.dict(), f, indent=4, ensure_ascii=False)
        logging.info(f"Updated appointment {appointment_id}")
        return appointment
    except Exception as e:
        logging.error(f"Error updating appointment {appointment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error updating appointment")

@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(appointment_id: str):
    if not appointment_exists(appointment_id):
        raise HTTPException(status_code=404, detail="Appointment not found")
    try:
        os.remove(appointment_file_path(appointment_id))
        logging.info(f"Deleted appointment {appointment_id}")
        return {"message": "Appointment deleted successfully"}
    except Exception as e:
        logging.error(f"Error deleting appointment {appointment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error deleting appointment")

# ----------------------------
# Manual reminder endpoint
# ----------------------------
@router.post("/send_reminder/{appointment_id}")
async def send_reminder_endpoint(appointment_id: str):
    if not appointment_exists(appointment_id):
        raise HTTPException(status_code=404, detail="Appointment not found")
    try:
        with open(appointment_file_path(appointment_id), "r", encoding="utf-8") as f:
            appointment_data = json.load(f)

        if not patient_exists(appointment_data["patient_id"]):
            raise HTTPException(status_code=404, detail="Patient not found")

        with open(patient_file_path(appointment_data["patient_id"]), "r", encoding="utf-8") as pf:
            patient_data = json.load(pf)

        result = schedule_reminders(appointment_data, patient_data.get("email"))
        logging.info(f"Sent reminder for appointment {appointment_id}")
        return {"message": result}
    except Exception as e:
        logging.error(f"Error sending reminder for {appointment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error sending reminder")
