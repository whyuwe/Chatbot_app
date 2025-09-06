import streamlit as st
import requests
import pandas as pd

API_URL = "http://127.0.0.1:8000/insurance"  # Backend API URL

def show_insurance():
    st.title("Insurance Records")
    
    menu = ["View Insurance", "Add Insurance", "Search & Filter", "Generate Report"]
    choice = st.selectbox("Select Action", menu)
    
    # ------------------ VIEW ------------------
    # ------------------ VIEW ------------------
    if choice == "View Insurance":
        try:
            res = requests.get(API_URL)
            if res.status_code == 200:
                insurances = res.json()
                if insurances:
                    df = pd.DataFrame(insurances)
                    page_size = 10  # Records per page
                    total_records = len(df)
                    total_pages = (total_records + page_size - 1) // page_size
                    
                    # Initialize current page in session state
                    if "insurance_page" not in st.session_state:
                        st.session_state.insurance_page = 1
                    
                    # Previous / Next buttons
                    col1, col2, col3 = st.columns([1,2,1])
                    with col1:
                        if st.button("⬅️ Previous") and st.session_state.insurance_page > 1:
                            st.session_state.insurance_page -= 1
                    with col3:
                        if st.button("Next ➡️") and st.session_state.insurance_page < total_pages:
                            st.session_state.insurance_page += 1
                    
                    current_page = st.session_state.insurance_page
                    start_idx = (current_page - 1) * page_size
                    end_idx = start_idx + page_size
                    
                    st.dataframe(df.iloc[start_idx:end_idx])
                    st.info(f"Showing records {start_idx + 1} to {min(end_idx, total_records)} of {total_records} (Page {current_page}/{total_pages})")
                else:
                    st.info("No insurance records found.")
            else:
                st.error(f"Failed to fetch insurance records: {res.status_code}")
        except Exception as e:
            st.error(f"Error fetching insurance records: {e}")

        
        # ------------------ ADD ------------------
    elif choice == "Add Insurance":
        st.subheader("Add New Insurance Record")
        with st.form(key="add_insurance"):
            insurance_id = st.text_input("Insurance ID")
            patient_id = st.text_input("Patient ID")
            carrier = st.text_input("Carrier")
            member_id = st.text_input("Member ID")
            group_no = st.text_input("Group No (optional)")
            coverage = st.selectbox("Coverage Type", ["Basic", "Premium", "Gold", "Platinum"])
            
            submitted = st.form_submit_button("Save Insurance")
            if submitted:
                payload = {
                    "insurance_id": insurance_id,
                    "patient_id": patient_id,
                    "carrier": carrier,
                    "member_id": member_id,
                    "group_no": group_no or None,
                    "coverage": coverage
                }
                try:
                    res = requests.post(API_URL, json=payload)
                    if res.status_code == 201:
                        st.success("Insurance record saved successfully")
                    else:
                        st.error(f"Error: {res.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Error saving insurance: {e}")
        
        # ------------------ SEARCH & FILTER ------------------
    elif choice == "Search & Filter":
        st.subheader("Search & Filter Insurance Records")
        search_carrier = st.text_input("Search by Carrier")
        coverage_filter = st.selectbox("Filter by Coverage", ["", "Basic", "Premium", "Gold", "Platinum"])
        
        if st.button("Search"):
            params = {
                "carrier": search_carrier if search_carrier else None,
                "coverage": coverage_filter if coverage_filter else None
            }
            params = {k: v for k, v in params.items() if v}

            try:
                res = requests.get(f"{API_URL}/search", params=params)
                if res.status_code == 200:
                    data = res.json().get("results", [])
                    if data:
                        df = pd.DataFrame(data)
                        st.dataframe(df)
                    else:
                        st.warning("No insurance records found.")
                else:
                    st.error("Error fetching insurance data.")
            except Exception as e:
                st.error(f"Error: {e}")
        
        # ------------------ REPORT ------------------
    elif choice == "Generate Report":
        try:
            res = requests.get(API_URL)
            if res.status_code == 200:
                df = pd.DataFrame(res.json())
                if not df.empty:
                    excel_file = "Insurance_Report.xlsx"
                    df.to_excel(excel_file, index=False)
                    with open(excel_file, "rb") as f:
                        st.download_button(
                            label="Download Insurance Report",
                            data=f,
                            file_name=excel_file,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    st.success("Report generated successfully!")
                else:
                    st.info("No records to generate report.")
            else:
                st.error(f"Failed to fetch insurance records: {res.status_code}")
        except Exception as e:
            st.error(f"Error generating report: {e}")
show_insurance()
