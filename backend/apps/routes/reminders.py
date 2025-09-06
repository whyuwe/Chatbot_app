import os, json
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler

# ----------------------------
# Scheduler
# ----------------------------
scheduler = BackgroundScheduler()
scheduler.start()

# ----------------------------
# Paths
# ----------------------------
PATIENT_FOLDER = "data/patient"
APPOINTMENT_FOLDER = "data/appointments"
LOG_FOLDER = "logs"

os.makedirs(APPOINTMENT_FOLDER, exist_ok=True)
os.makedirs(LOG_FOLDER, exist_ok=True)

# ----------------------------
# Email Configuration
# ----------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "your_email@gmail.com"       # Replace with your email
EMAIL_PASSWORD = "your_app_password"         # Use App Password if Gmail

def send_email(recipient_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"Email sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"Failed to send email to {recipient_email}: {e}")
        return False

# ----------------------------
# Load patient data dynamically
# ----------------------------
def load_patient(patient_id):
    path = os.path.join(PATIENT_FOLDER, f"patient{patient_id}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None

# ----------------------------
# Book Appointment
# ----------------------------
def book_appointment(patient_id, preferred_date=None, patient_email=None):
    date_str = preferred_date if preferred_date else datetime.now().strftime("%Y-%m-%d")
    patient_file = os.path.join(APPOINTMENT_FOLDER, f"{patient_id}.json")

    # Load existing appointments
    if os.path.exists(patient_file):
        with open(patient_file, "r") as f:
            appointment = json.load(f)
    else:
        appointment = {}

    # Simple 1-hour slot system 9am-5pm
    slots = [f"{h}:00-{h+1}:00" for h in range(9, 17)]
    used_slots = [appt["slot"] for appt in appointment.get("appointments", [])]
    available_slot = next((s for s in slots if s not in used_slots), None)

    if not available_slot:
        next_day = (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        return book_appointment(patient_id, next_day, patient_email)

    new_appt = {
        "appointment_id": f"A{len(used_slots)+1:03d}",
        "patient_id": patient_id,
        "date": date_str,
        "slot": available_slot,
        "status": "upcoming",
        "reminders_sent": []
    }

    appointment.setdefault("appointments", []).append(new_appt)

    # Save appointment JSON
    with open(patient_file, "w") as f:
        json.dump(appointment, f, indent=4)

    # Schedule reminders automatically
    schedule_reminders(new_appt, patient_email)

    return new_appt

# ----------------------------
# Send Reminder
# ----------------------------
def send_reminder(appointment, patient_email=None, reminder_type=None):
    if reminder_type is None:
        reminder_type = f"Reminder-{len(appointment.get('reminders_sent', []))+1}"

    # Avoid duplicate reminders
    if reminder_type in appointment.get("reminders_sent", []):
        return

    appointment.setdefault("reminders_sent", []).append(reminder_type)

    # Save back
    patient_file = os.path.join(APPOINTMENT_FOLDER, f"{appointment['patient_id']}.json")
    if os.path.exists(patient_file):
        with open(patient_file, "r") as f:
            data = json.load(f)
        # Update the appointment in the list
        for idx, appt in enumerate(data.get("appointments", [])):
            if appt["appointment_id"] == appointment["appointment_id"]:
                data["appointments"][idx] = appointment
        with open(patient_file, "w") as f:
            json.dump(data, f, indent=4)

    # Send email
    if patient_email:
        subject = f"Appointment Reminder ({reminder_type})"
        body = f"Dear Patient {appointment['patient_id']},\nYour appointment is scheduled on {appointment['date']} at {appointment['slot']}.\nThis is your {reminder_type}."
        send_email(patient_email, subject, body)

    # Log reminder
    with open(os.path.join(LOG_FOLDER, "reminders_log.txt"), "a") as f:
        f.write(f"{datetime.now()}: {reminder_type} sent to {appointment['patient_id']}\n")
    print(f"{reminder_type} sent to {appointment['patient_id']}")

# ----------------------------
# Schedule Reminders
# ----------------------------
def schedule_reminders(appointment, patient_email=None):
    appt_datetime = datetime.strptime(f"{appointment['date']} {appointment['slot'].split('-')[0]}", "%Y-%m-%d %H:%M")

    reminders = [
        ("Reminder-60min", appt_datetime - timedelta(minutes=60)),
        ("Reminder-30min", appt_datetime - timedelta(minutes=30)),
        ("Final-Reminder", appt_datetime)
    ]

    for r_type, r_time in reminders:
        if r_time > datetime.now():
            scheduler.add_job(send_reminder, 'date', run_date=r_time, args=[appointment, patient_email, r_type])
