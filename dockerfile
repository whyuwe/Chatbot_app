# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . .

# Expose ports for backend and frontend
EXPOSE 8000
EXPOSE 8501

# Environment variables for Streamlit
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ENABLECORS=false

# Run both backend and frontend
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port 8000 & streamlit run frontend.app.py --server.port 8501 --server.address 0.0.0.0"]
