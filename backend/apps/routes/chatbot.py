from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
import os, json, shutil, logging

from ..routes.patients import patient_exists, patient_file_path
from ..routes.appointments import create_appointment, AppointmentModel

# LangChain imports
from langchain.chains import create_retrieval_chain
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.text_splitter import CharacterTextSplitter

# OCR + PDF
import pytesseract
from PIL import Image
import PyPDF2

router = APIRouter()

# ----------------------------
# Logging configuration
# ----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("chatbot.log"),
        logging.StreamHandler()
    ]
)

PDF_FOLDER = os.path.join("apps", "data", "forms")
VECTORSTORE_FILE = os.path.join(PDF_FOLDER, "vectorstore.faiss")
os.makedirs(PDF_FOLDER, exist_ok=True)

# ---------------------------- Pydantic models ----------------------------
class ChatResponse(BaseModel):
    response: str
    summary: Optional[List[str]] = None
    appointment_suggestion: Optional[str] = None

# ---------------------------- Utilities ----------------------------
def load_vectorstore():
    if os.path.exists(VECTORSTORE_FILE):
        try:
            return FAISS.load_local(VECTORSTORE_FILE, OpenAIEmbeddings())
        except Exception as e:
            logging.error(f"Error loading vectorstore: {e}")
    return None

def ocr_image(file_path: str) -> str:
    try:
        return pytesseract.image_to_string(Image.open(file_path))
    except Exception as e:
        logging.error(f"OCR failed for {file_path}: {e}")
        return ""

def extract_text_from_pdf(file_path: str) -> str:
    try:
        text = ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logging.error(f"PDF extraction failed for {file_path}: {e}")
        return ""

def add_to_vectorstore(texts: List[str]):
    global vectorstore
    if vectorstore is None:
        vectorstore = FAISS.from_texts(texts, OpenAIEmbeddings())
    else:
        vectorstore.add_texts(texts)
    vectorstore.save_local(VECTORSTORE_FILE)

vectorstore = load_vectorstore()

# ---------------------------- Prompts ----------------------------
SUMMARY_PROMPT_TEMPLATE = PromptTemplate(
    input_variables=["patient_name", "message"],
    template="Patient {patient_name} asked: {message}\nProvide a concise summary in 4-5 bullet points."
)

RAG_PROMPT_TEMPLATE = PromptTemplate(
    input_variables=["user_question"],
    template="Answer the following patient query using retrieved documents:\n{user_question}"
)

# ---------------------------- Chat endpoint ----------------------------
@router.post("/chat_with_file", response_model=ChatResponse)
async def chat_with_file(
    patient_id: str = Form(...),
    message: str = Form(...),
    use_rag: bool = Form(True),
    file: Optional[UploadFile] = File(None)
):
    try:
        if not patient_exists(patient_id):
            raise HTTPException(status_code=404, detail="Patient not found")

        with open(patient_file_path(patient_id), "r", encoding="utf-8") as f:
            patient = json.load(f)
        patient_name = patient.get("name", f"Patient {patient_id}")

        llm = ChatOpenAI(temperature=0)
        user_message = message.strip()
        rag_context = ""
        summary_points = []

        # Summarize
        try:
            summary_prompt = SUMMARY_PROMPT_TEMPLATE.format(patient_name=patient_name, message=user_message)
            summary_response = llm.predict(summary_prompt)
            summary_points = [line.strip() for line in summary_response.split("\n") if line.strip()][:5]
        except Exception as e:
            logging.warning(f"Summarization failed: {e}")
            summary_points = [f"Error generating summary: {e}"]

        # Process uploaded file and perform RAG retrieval
        if file and use_rag:
            file_path = os.path.join(PDF_FOLDER, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            ext = file.filename.split(".")[-1].lower()
            if ext in ["png", "jpg", "jpeg"]:
                extracted_text = ocr_image(file_path)
            elif ext == "pdf":
                extracted_text = extract_text_from_pdf(file_path)
            else:
                extracted_text = ""

            if extracted_text.strip():
                splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
                chunks = splitter.split_text(extracted_text)
                add_to_vectorstore(chunks)
                logging.info(f"{file.filename} uploaded and indexed for patient {patient_id}")

            try:
                if vectorstore:
                    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})
                    qa_chain = create_retrieval_chain(
                        llm=llm,
                        retriever=retriever,
                        chain_type="stuff",
                        chain_type_kwargs={"prompt": RAG_PROMPT_TEMPLATE},
                        return_source_documents=False
                    )
                    rag_context = qa_chain.run(user_message).strip()
            except Exception as e:
                logging.warning(f"RAG retrieval failed: {e}")

        full_response = "\n".join(filter(bool, [rag_context] + summary_points))
        appointment_suggestion = None

        if "appointment" in user_message.lower() or "book" in user_message.lower():
            appointment_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logging.info(f"Attempting to schedule appointment for patient {patient_id}")
            appointment_suggestion = f"Appointment scheduled for {patient_name} on {appointment_time}."

        logging.info(f"Chat response for {patient_id}: {full_response}")
        return ChatResponse(
            response=full_response,
            summary=summary_points,
            appointment_suggestion=appointment_suggestion
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Error in chat_with_file endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
