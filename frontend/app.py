import streamlit as st
import os

# ----------------------------
# Page config
# ----------------------------
st.set_page_config(page_title="Raga AI Medical Assistant", layout="wide")

# ----------------------------
# Welcome Message
# ----------------------------
if 'show_welcome' not in st.session_state:
    st.session_state.show_welcome = True

if st.session_state.show_welcome:
    st.title("Welcome to Raga AI Medical Assistant 🤖💊")
    st.markdown(
        """
        Raga AI Medical Assistant helps you manage patients, appointments, insurance,
        forms, and medical reports all in one place. Navigate using the sidebar to get started.
        """
    )

# ----------------------------
# Sidebar Navigation
# ----------------------------
st.sidebar.title("Navigation")
menu_options = [
    "Dashboard",
    "Patients",
    "Appointments",
    "Insurance",
    "Forms",
    "Chatbot",
    "Generate Report"
]
choice = st.sidebar.radio("Go to", menu_options)

# If a page is selected, hide welcome message
if choice:
    st.session_state.show_welcome = False

# ----------------------------
# Map sidebar choice to page scripts
# ----------------------------
page_mapping = {
    "Dashboard": "pages/dashboard_page.py",
    "Patients": "pages/patients_page.py",
    "Appointments": "pages/appointments_page.py",
    "Insurance": "pages/insurance_page.py",
    "Forms": "pages/forms_page.py",
    "Chatbot": "pages/chatbot_page.py",
    "Generate Report": "pages/report_page.py",
}

page_to_run = page_mapping.get(choice)


# ----------------------------
if page_to_run and os.path.exists(page_to_run):
    # Clear the welcome message before running the page
    if not st.session_state.show_welcome:
        st.empty()  # remove welcome section
    with open(page_to_run, "r", encoding="utf-8") as f:
        code = f.read()
        exec(code)
else:
    if not st.session_state.show_welcome:
        st.error(f"Page '{choice}' not found!")
