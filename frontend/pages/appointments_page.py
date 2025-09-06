import streamlit as st
import requests
import pandas as pd
import io
from datetime import datetime, date

# ----------------------------
# Page Config
# ----------------------------
st.set_page_config(page_title="Raga AI Medical Assistant: Appointments", layout="wide")
st.title("Raga AI Medical Assistant: Appointments Management")
st.write("Manage appointments easily. Select an action below:")

# ----------------------------
# Backend URLs
# ----------------------------
API_PATIENTS = "http://127.0.0.1:8000/patients"
API_APPT_BASE = "http://127.0.0.1:8000/appointments"   # list/create lives at /appointments/
API_APPT_LIST_CREATE = f"{API_APPT_BASE}/"

# ----------------------------
# Session State
# ----------------------------
if "appointments_list" not in st.session_state:
    st.session_state.appointments_list = []

if "patients_list" not in st.session_state:
    st.session_state.patients_list = []

if "action" not in st.session_state:
    st.session_state.action = "View / Filter Appointments"

# ----------------------------
# Fetchers
# ----------------------------
def fetch_patients():
    try:
        res = requests.get(API_PATIENTS, timeout=5)
        res.raise_for_status()
        st.session_state.patients_list = res.json()
    except Exception as e:
        st.warning(f"Could not fetch patients: {e}")
        st.session_state.patients_list = []

def fetch_appointments():
    try:
        res = requests.get(API_APPT_LIST_CREATE, timeout=5)
        res.raise_for_status()
        st.session_state.appointments_list = res.json()
    except Exception as e:
        st.warning(f"Could not fetch appointments: {e}")
        st.session_state.appointments_list = []

fetch_patients()
fetch_appointments()

patient_options = [f"{p['patient_id']} | {p['name']}" for p in st.session_state.patients_list]

df_appts = pd.DataFrame(st.session_state.appointments_list)
if not df_appts.empty:
    if 'date' in df_appts.columns:
        df_appts['date'] = pd.to_datetime(df_appts['date'], errors='coerce')
    if 'reminders_sent' in df_appts.columns:
        df_appts['reminders_sent'] = df_appts['reminders_sent'].apply(lambda x: ", ".join(x) if x else "None")

# ----------------------------
# CRUD Helpers (no auto-calls!)
# ----------------------------
def book_appointment(payload):
    try:
        res = requests.post(API_APPT_LIST_CREATE, json=payload, timeout=5)
        res.raise_for_status()
        st.success("Appointment booked successfully!")
        fetch_appointments()
        st.experimental_rerun()
    except Exception as e:
        # Try to show backend detail if present
        try:
            detail = res.json().get("detail")
            st.error(f"Error booking appointment: {detail or e}")
        except Exception:
            st.error(f"Error booking appointment: {e}")

def update_appointment(appt_id, payload):
    try:
        res = requests.put(f"{API_APPT_BASE}/{appt_id}", json=payload, timeout=5)
        res.raise_for_status()
        st.success("Appointment updated successfully!")
        fetch_appointments()
        st.rerun()
    except Exception as e:
        try:
            detail = res.json().get("detail")
            st.error(f"Error updating appointment: {detail or e}")
        except Exception:
            st.error(f"Error updating appointment: {e}")

def delete_appointment(appt_id):
    try:
        res = requests.delete(f"{API_APPT_BASE}/{appt_id}", timeout=5)
        res.raise_for_status()
        st.success("Appointment deleted successfully!")
        fetch_appointments()
        st.rerun()
    except Exception as e:
        try:
            detail = res.json().get("detail")
            st.error(f"Error deleting appointment: {detail or e}")
        except Exception:
            st.error(f"Error deleting appointment: {e}")

def send_reminder(appt_id):
    try:
        res = requests.post(f"{API_APPT_BASE}/send_reminder/{appt_id}", timeout=5)
        res.raise_for_status()
        st.success(res.json().get("message", "Reminder sent!"))
    except Exception as e:
        try:
            detail = res.json().get("detail")
            st.error(f"Error sending reminder: {detail or e}")
        except Exception:
            st.error(f"Error sending reminder: {e}")

# ----------------------------
# Action Selector
# ----------------------------
st.session_state.action = st.selectbox(
    "Select Action",
    ["View / Filter Appointments", "Book New Appointment", "Update/Delete/Send Reminder"],
    index=["View / Filter Appointments", "Book New Appointment", "Update/Delete/Send Reminder"].index(st.session_state.action)
)

# ----------------------------
# Section 1: View / Filter
# ----------------------------
if st.session_state.action == "View / Filter Appointments":
    st.subheader("View / Filter Appointments")

    col1, col2 = st.columns(2)
    filter_patient = col1.selectbox("Filter by Patient", ["All"] + patient_options)
    filter_status = col2.selectbox("Filter by Status", ["All", "upcoming", "completed", "cancelled"])

    col3, col4 = st.columns(2)
    filter_from = col3.date_input("From Date", value=date.today())
    filter_to = col4.date_input("To Date", value=date.today())

    filtered_df = df_appts.copy() if not df_appts.empty else pd.DataFrame()
    if not filtered_df.empty:
        if filter_patient != "All":
            patient_id = filter_patient.split(" | ")[0]
            filtered_df = filtered_df[filtered_df['patient_id'] == patient_id]
        if filter_status != "All":
            filtered_df = filtered_df[filtered_df['status'] == filter_status]
        filtered_df = filtered_df[
            (filtered_df['date'] >= pd.to_datetime(filter_from)) &
            (filtered_df['date'] <= pd.to_datetime(filter_to))
        ]

        st.dataframe(filtered_df, use_container_width=True)

        # Excel report
        if st.button("Generate Excel Report"):
            buffer = io.BytesIO()
            filtered_df.to_excel(buffer, index=False)
            buffer.seek(0)
            st.download_button(
                "Download Report",
                buffer,
                "Appointments_Report.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("No appointments available to display.")

# ----------------------------
# Section 2: Book New Appointment
# ----------------------------
elif st.session_state.action == "Book New Appointment":
    st.subheader("Book New Appointment")
    if not patient_options:
        st.warning("No patients available. Add patients first in the backend.")
    else:
        with st.form("book_form"):
            appt_id = st.text_input("Appointment ID")
            selected_patient = st.selectbox("Select Patient", patient_options)
            patient_id = selected_patient.split(" | ")[0]
            appt_date = st.date_input("Date", value=date.today())
            slot = st.text_input("Slot (HH:MM-HH:MM)", "09:00-09:30")
            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Book Appointment")
            if submitted:
                payload = {
                    "appointment_id": appt_id,
                    "patient_id": patient_id,
                    "date": appt_date.strftime("%Y-%m-%d"),
                    "slot": slot,
                    "status": "upcoming",
                    "notes": notes,
                    "reminders_sent": []
                }
                book_appointment(payload)

# ----------------------------
# Section 3: Update / Delete / Send Reminder
# ----------------------------
elif st.session_state.action == "Update/Delete/Send Reminder":
    st.subheader("Update / Delete / Send Reminder")
    appt_id = st.text_input("Enter Appointment ID")
    if appt_id:
        appt_data = next((a for a in st.session_state.appointments_list if a.get("appointment_id") == appt_id), None)
        if appt_data:
            st.info(f"Editing Appointment {appt_id}")
            with st.form("update_form"):
                # Default-select current patient
                current_label = next(
                    (f"{p['patient_id']} | {p['name']}" for p in st.session_state.patients_list if p['patient_id'] == appt_data['patient_id']),
                    None
                )
                idx = patient_options.index(current_label) if current_label in patient_options else 0
                selected_patient = st.selectbox("Patient", patient_options, index=idx)
                patient_id = selected_patient.split(" | ")[0]

                update_date = st.date_input("Date", datetime.strptime(appt_data['date'], "%Y-%m-%d"))
                update_slot = st.text_input("Slot", appt_data['slot'])
                update_status = st.selectbox(
                    "Status",
                    ["upcoming", "completed", "cancelled"],
                    index=["upcoming", "completed", "cancelled"].index(appt_data['status'])
                )
                update_notes = st.text_area("Notes", appt_data.get('notes', ""))

                colu1, colu2, colu3 = st.columns(3)
                update_submit = colu1.form_submit_button("Update")
                delete_submit = colu2.form_submit_button("Delete")
                reminder_submit = colu3.form_submit_button("Send Reminder")

                if update_submit:
                    payload = {
                        "appointment_id": appt_id,
                        "patient_id": patient_id,
                        "date": update_date.strftime("%Y-%m-%d"),
                        "slot": update_slot,
                        "status": update_status,
                        "notes": update_notes,
                        "reminders_sent": appt_data.get("reminders_sent", [])
                    }
                    update_appointment(appt_id, payload)
                if delete_submit:
                    delete_appointment(appt_id)
                if reminder_submit:
                    send_reminder(appt_id)
        else:
            st.warning(f"No appointment found with ID {appt_id}.")
