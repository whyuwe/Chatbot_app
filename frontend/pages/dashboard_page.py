import streamlit as st
import pandas as pd
import requests
import time # Added for auto-refresh

# Note: For production, this URL should be a stable, public address
# and not a local development one.
BASE_URL = "http://127.0.0.1:8000/dashboard"

# ----------------------------
# Function to fetch dashboard stats
# ----------------------------
def get_dashboard_data(search=None, insurance=None):
    """Fetches dashboard data from the backend API."""
    try:
        params = {}
        if search:
            params["search"] = search
        if insurance:
            params["insurance"] = insurance

        response = requests.get(BASE_URL, params=params)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch dashboard data. Error: {e}")
        return {}

# ----------------------------
# Main Page
# ----------------------------
def show_page():
    """Renders the main dashboard page."""
    st.set_page_config(page_title="📊 Dashboard", layout="wide")

    # Sidebar refresh control
    refresh_interval = st.sidebar.slider("🔄 Refresh Interval (seconds)", 5, 60, 10)

    # Auto-refresh using a simple loop and rerun
    # Note: st.rerun will stop execution and re-run from the top
    if st.button("Start Auto-Refresh"):
        st.info(f"Auto-refresh is active every {refresh_interval} seconds. Click 'Stop' to disable.")
        while True:
            time.sleep(refresh_interval)
            st.rerun()

    # Search & Filter
    col1, col2 = st.columns([2, 1])
    search = col1.text_input("🔍 Search by Name or Patient ID")
    insurance_filter = col2.selectbox(
        "🏥 Filter by Insurance",
        ["", "Aetna", "BlueCross", "UnitedHealth", "Medicare"]
    )

    # Fetch data
    data = get_dashboard_data(search, insurance_filter)
    if not data:
        st.warning("No data available or backend is not reachable.")
        return

    # Title
    st.title("📊 Dashboard (Live)")

    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Patients", data.get("total_patients", 0))
    col2.metric("Total Appointments", data.get("total_appointments", 0))
    col3.metric("Upcoming Appointments", data.get("upcoming_appointments", 0))

    col1, col2, col3 = st.columns(3)
    col1.metric("Completed Appointments", data.get("completed_appointments", 0))
    col2.metric("Total Forms", data.get("total_forms", 0))
    col3.metric("Processed Forms", data.get("processed_forms", 0))

    # Charts
    st.subheader("📊 Age Distribution")
    # Convert age_distribution dict to a DataFrame for plotting
    age_df = pd.DataFrame(
        data.get("age_distribution", {}).items(),
        columns=["Age Group", "Count"]
    ).sort_values("Age Group")
    if not age_df.empty:
        st.bar_chart(age_df, x="Age Group", y="Count")
    else:
        st.info("No age distribution data to display.")

    st.subheader("📅 Appointments per Patient")
    # Convert appointments_per_patient dict to a DataFrame
    appts_df = pd.DataFrame(
        data.get("appointments_per_patient", {}).items(),
        columns=["Patient ID", "Appointments"]
    )
    if not appts_df.empty:
        st.bar_chart(appts_df, x="Patient ID", y="Appointments")
    else:
        st.info("No appointments per patient data to display.")

    # Patients List
    st.subheader("👥 Patients List")
    patients_df = pd.DataFrame(data.get("patients", []))
    if not patients_df.empty:
        st.dataframe(patients_df)
        
        # Excel Export
        excel_file = "dashboard_report.xlsx"
        patients_df.to_excel(excel_file, index=False)
        with open(excel_file, "rb") as f:
            st.download_button(
                "📥 Download Report",
                f,
                file_name="dashboard_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("No patient data available.")

    # Manual refresh button
    if st.button("🔄 Refresh Now"):
        st.rerun()

get_dashboard_data()
show_page()         
