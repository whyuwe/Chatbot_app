import streamlit as st
import requests
import pandas as pd
import io
from datetime import date

API_URL = "http://127.0.0.1:8000/patients"  # Backend API URL
st.title("Patients Management")

def show_patients():
    

    menu = ["View Patients", "Add Patient", "Generate Report"]
    choice = st.selectbox("Select Action", menu)

    # ----------------------------
    # Section 1: View Patients
    # ----------------------------
    if choice == "View Patients":
        try:
            res = requests.get(API_URL)
            res.raise_for_status()
            patients = res.json()

            if patients:
                df = pd.DataFrame(patients)

                # Convert DOB to datetime
                if 'dob' in df.columns:
                    df['dob'] = pd.to_datetime(df['dob'], errors='coerce')

                # Search & Filter Section
                st.subheader("Search & Filter")
                name_filter = st.text_input("Search by Name")
                gender_filter = st.multiselect("Filter by Gender", df["gender"].unique())
                dob_filter = st.date_input("Filter by DOB", value=None)

                # Apply filters
                filtered_df = df.copy()
                if name_filter:
                    filtered_df = filtered_df[filtered_df["name"].str.contains(name_filter, case=False, na=False)]
                if gender_filter:
                    filtered_df = filtered_df[filtered_df["gender"].isin(gender_filter)]
                if dob_filter:
                    filtered_df = filtered_df[filtered_df['dob'] == pd.to_datetime(dob_filter)]

                st.write(f"Showing {len(filtered_df)} results")
                st.dataframe(filtered_df, use_container_width=True)

            else:
                st.info("No patient records found.")

        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching patients: {e}")

    # ----------------------------
    # Section 2: Add Patient
    # ----------------------------
    elif choice == "Add Patient":
        st.subheader("Add New Patient")
        with st.form(key="add_patient_form"):
            patient_id = st.text_input("Patient ID")
            name = st.text_input("Name")
            dob_input = st.date_input("Date of Birth", value=date.today())
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])
            phone = st.text_input("Phone")
            email = st.text_input("Email")
            address = st.text_area("Address")
            submitted = st.form_submit_button("Save Patient")

            if submitted:
                payload = {
                    "patient_id": patient_id,
                    "name": name,
                    "dob": dob_input.strftime("%Y-%m-%d"),
                    "gender": gender,
                    "phone": phone,
                    "email": email,
                    "address": address
                }
                try:
                    res = requests.post(API_URL, json=payload)
                    if res.status_code in [200, 201]:
                        st.success("Patient saved successfully!")
                        st.rerun()
                    else:
                        st.error(f"Error: {res.json().get('detail', 'Unknown error')}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Error saving patient: {e}")

    # ----------------------------
    # Section 3: Generate Excel Report
    # ----------------------------
    elif choice == "Generate Report":
        st.subheader("Generate Patients Excel Report")
        try:
            res = requests.get(API_URL)
            res.raise_for_status()
            patients = res.json()

            if patients:
                df = pd.DataFrame(patients)
                buffer = io.BytesIO()
                df.to_excel(buffer, index=False)
                buffer.seek(0)

                st.download_button(
                    label="Download Patients Report",
                    data=buffer,
                    file_name="Patients_Report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("No patient data available to generate report.")

        except requests.exceptions.RequestException as e:
            st.error(f"Error generating report: {e}")


show_patients()            
