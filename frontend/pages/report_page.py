import streamlit as st
import requests
import pandas as pd
from io import BytesIO

API_URL = "http://127.0.0.1:8000 "

def show_report():
    st.title("Generate Consolidated Report")
    st.info("This will create an Excel report with all patients, appointments, insurance, and forms data, including reminders sent.")

    if st.button("Generate Report"):
        try:
            # Fetch data from all endpoints
            endpoints = {
                "Patients": "/patients/",
                "Appointments": "/appointments/",
                "Insurance": "/insurance/",
                "Forms": "/forms/"
            }

            # Create a BytesIO buffer to store Excel file in-memory
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                for sheet_name, endpoint in endpoints.items():
                    res = requests.get(f"{API_URL}{endpoint}")
                    if res.status_code == 200:
                        data = res.json()
                        if data:
                            df = pd.DataFrame(data)

                            # Handle reminders_sent for Appointments
                            if sheet_name == "Appointments":
                                if "reminders_sent" in df.columns:
                                    df["reminders_sent"] = df["reminders_sent"].apply(
                                        lambda x: ", ".join(x) if x else "None"
                                    )
                                else:
                                    df["reminders_sent"] = "None"

                            df.to_excel(writer, sheet_name=sheet_name, index=False)
                        else:
                            # Empty sheet message
                            pd.DataFrame([{"Info": f"No {sheet_name.lower()} data"}]).to_excel(writer, sheet_name=sheet_name, index=False)
                    else:
                        pd.DataFrame([{"Error": f"Failed to fetch {sheet_name.lower()}"}]).to_excel(writer, sheet_name=sheet_name, index=False)

            # Prepare download button
            st.success("Consolidated report generated successfully!")
            st.download_button(
                label="Download Excel Report",
                data=output.getvalue(),
                file_name="Consolidated_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"Error generating report: {e}")

show_report()            
