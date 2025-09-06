# main.py
"""
AI Scheduling Agent Backend Entry Point
This file initializes the FastAPI app, includes all route modules,
and provides endpoints with Pydantic validation, automatic saving, logging,
and filtering for appointments.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, ValidationError
from typing import Optional, List
import os
import json
import logging
from datetime import datetime

from apps.routes import patients, appointments, insurance, forms, dashboard, chatbot

# ----------------------------
# Configure Logging (Direct in main.py)
# ----------------------------
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "access.log")),
        logging.FileHandler(os.path.join(LOG_DIR, "error.log")),
        logging.StreamHandler()
    ]
)

def log_info(message: str):
    logging.info(message)

def log_error(message: str):
    logging.error(message)

# ----------------------------
# Initialize FastAPI app
# ----------------------------
app = FastAPI(
    title="AI Scheduling Agent Backend",
    description="Backend API for managing patients, appointments, insurance, forms, and chatbot interactions.",
    version="1.0.1"
)

# ----------------------------
# CORS Middleware
# ----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Pydantic models for validation
# ----------------------------
class PatientModel(BaseModel):
    patient_id: str = Field(..., example="001")
    name: str = Field(..., min_length=2, max_length=50)
    dob: str = Field(..., pattern=r"\d{4}-\d{2}-\d{2}", example="1985-07-15")
    gender: str = Field(..., pattern=r"^(Male|Female|Other)$")
    phone: str = Field(..., pattern=r"^\d{10}$", example="9876543210")
    email: EmailStr
    address: str
    insurance: Optional[dict] = Field(None, example={"carrier": "MediCare", "member_id": "AB12345"})

class AppointmentModel(BaseModel):
    appointment_id: str
    patient_id: str
    date: str = Field(..., pattern=r"\d{4}-\d{2}-\d{2}")
    slot: str = Field(..., example="09:00-09:30")
    status: str = Field(..., pattern=r"^(upcoming|completed|cancelled)$")
    notes: Optional[str] = None
    reminders_sent: Optional[List[str]] = []

# ----------------------------
# Health Check Endpoint
# ----------------------------
@app.get("/ping")
async def ping():
    return {"status": "ok"}

# ----------------------------
# Save directory paths
# ----------------------------
PATIENT_DIR = os.path.join("app", "data", "patients")
APPOINTMENT_DIR = os.path.join("app", "data", "appointments")
os.makedirs(PATIENT_DIR, exist_ok=True)
os.makedirs(APPOINTMENT_DIR, exist_ok=True)

# ----------------------------
# Appointment CRUD + Filtering
# ----------------------------
def appointment_file_path(appointment_id: str) -> str:
    return os.path.join(APPOINTMENT_DIR, f"{appointment_id}.json")

def appointment_exists(appointment_id: str) -> bool:
    return os.path.exists(appointment_file_path(appointment_id))

def read_all_appointments() -> List[dict]:
    result = []
    for f in os.listdir(APPOINTMENT_DIR):
        if f.endswith('.json'):
            try:
                with open(os.path.join(APPOINTMENT_DIR, f), 'r', encoding='utf-8') as file:
                    result.append(json.load(file))
            except Exception as e:
                log_error(f"Failed to read {f}: {e}")
    return result

@app.get("/appointments/")
async def get_appointments(
    status: Optional[str] = Query(None, regex="^(upcoming|completed|cancelled)$"),
    patient_id: Optional[str] = None,
    date: Optional[str] = None
):
    """
    Get all appointments with optional filters: status, patient_id, date
    """
    try:
        appointments = read_all_appointments()
        if status:
            appointments = [a for a in appointments if a['status'] == status]
        if patient_id:
            appointments = [a for a in appointments if a['patient_id'] == patient_id]
        if date:
            appointments = [a for a in appointments if a['date'] == date]
        return appointments
    except Exception as e:
        log_error(f"Error fetching appointments: {e}")
        raise HTTPException(status_code=500, detail="Error fetching appointments")

@app.post("/appointments/")
async def create_appointment(appointment: AppointmentModel):
    if appointment_exists(appointment.appointment_id):
        raise HTTPException(status_code=400, detail="Appointment ID already exists")
    try:
        with open(appointment_file_path(appointment.appointment_id), 'w', encoding='utf-8') as f:
            json.dump(appointment.dict(), f, indent=4)
        log_info(f"Appointment {appointment.appointment_id} created")
        return {"message": "Appointment saved", "data": appointment}
    except Exception as e:
        log_error(f"Error saving appointment: {e}")
        raise HTTPException(status_code=500, detail="Error saving appointment")

# ----------------------------
# Include Modular Routers (existing reminder paths untouched)
# ----------------------------
app.include_router(patients.router, prefix="/patients", tags=["Patients"])
app.include_router(appointments.router, prefix="/appointments", tags=["Appointments"])
app.include_router(insurance.router, prefix="/insurance", tags=["Insurance"])
app.include_router(forms.router, prefix="/forms", tags=["Forms"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(chatbot.router, prefix="/chatbot", tags=["Chatbot"])

# ----------------------------
# Global exception handler
# ----------------------------
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    return {"error": "Validation failed", "details": exc.errors()}
