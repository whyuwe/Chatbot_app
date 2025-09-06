# Raga AI App

This is a combined **FastAPI Backend** and **Streamlit Frontend** project for managing patients, appointments, and forms with PDF upload and reminder features.

## 📌 Features
- **Backend (FastAPI)**
  - Patient management
  - Appointment booking, updating, deleting
  - Reminder sending via API
  - Data stored in JSON files

- **Frontend (Streamlit)**
  - View and manage patients
  - View, upload, and generate reports for forms
  - Appointment booking and reminder sending

## 🚀 Running with Docker
You can run both frontend and backend in one container.

### 1️⃣ Build the Docker image
```bash
docker build -t raga_ai_app .
