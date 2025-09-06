import streamlit as st
import requests
import pandas as pd

API_URL = "http://127.0.0.1:8000/forms"  # Backend API URL

def show_forms():
    st.title("Forms Management")
    
    menu = ["View Forms", "Upload Form", "Generate Report"]
    choice = st.selectbox("Select Action", menu)
    
    # ------------------ VIEW FORMS ------------------
    if choice == "View Forms":
        try:
            res = requests.get(API_URL)
            if res.status_code == 200:
                forms = res.json()
                if forms:
                    df = pd.DataFrame(forms)
                    st.dataframe(df)
                else:
                    st.info("No forms found.")
            else:
                st.error(f"Failed to fetch forms: {res.status_code}")
        except Exception as e:
            st.error(f"Error fetching forms: {e}")
    
    # ------------------ UPLOAD FORM ------------------
    elif choice == "Upload Form":
        st.subheader("Upload PDF Form")
        patient_id = st.text_input("Patient ID")
        file = st.file_uploader("Choose PDF", type=["pdf"])
        
        if st.button("Upload"):
            if not patient_id or not file:
                st.error("Please provide patient ID and select a PDF file")
            else:
                try:
                    files = {"file": (file.name, file, "application/pdf")}
                    res = requests.post(f"{API_URL}/upload?patient_id={patient_id}", files=files)
                    if res.status_code == 201:
                        st.success(f"Form uploaded successfully: {res.json().get('form_id', 'N/A')}")
                    else:
                        st.error(f"Error: {res.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Error uploading form: {e}")
    
    # ------------------ GENERATE REPORT ------------------
    elif choice == "Generate Report":
        try:
            res = requests.get(API_URL)
            if res.status_code == 200:
                df = pd.DataFrame(res.json())
                if not df.empty:
                    excel_file = "Forms_Report.xlsx"
                    df.to_excel(excel_file, index=False)
                    with open(excel_file, "rb") as f:
                        st.download_button(
                            label="Download Excel Report",
                            data=f,
                            file_name=excel_file,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    st.success("Report generated successfully!")
                else:
                    st.info("No forms to generate report.")
            else:
                st.error(f"Failed to fetch forms: {res.status_code}")
        except Exception as e:
            st.error(f"Error generating report: {e}")

show_forms()            
