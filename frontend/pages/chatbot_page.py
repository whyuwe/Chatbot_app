import streamlit as st
import streamlit.components.v1 as components
import requests
import json 

BASE_URL = "http://127.0.0.1:8000/chatbot"

# ----------------------------
# Page Config
# ----------------------------
st.set_page_config(page_title="Medical AI Assistant", layout="wide")

# ----------------------------
# Initialize chat history
# ----------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ----------------------------
# Page Title
# ----------------------------
st.title("🤖 Medical AI Assistant")
st.markdown("Type your question below or upload a PDF/Image to get responses from the AI assistant.")

# ----------------------------
# Simple Form Interface
# ----------------------------
col1, col2 = st.columns([1, 1])
with col1:
    patient_id = st.text_input("Patient ID:", value="001")
with col2:
    use_rag = st.checkbox("Use RAG", value=True)

with st.form(key="chat_form"):
    user_message = st.text_input("Ask your question here:")
    user_file = st.file_uploader("Upload a PDF/Image", type=["pdf", "png", "jpg", "jpeg"])
    submit_button = st.form_submit_button("Send")

if submit_button:
    if not user_message and not user_file:
        st.warning("Please type a message or upload a file before sending.")
    else:
        with st.spinner("Getting response from AI..."):
            try:
                form_data = {
                    "patient_id": patient_id,
                    "message": user_message,
                    "use_rag": str(use_rag).lower()
                }
                files = {"file": user_file} if user_file else None

                response = requests.post(f"{BASE_URL}/chat_with_file", data=form_data, files=files)
                response_data = response.json()
                bot_response = response_data.get("response", "No response from bot")

                st.session_state.chat_history.append(("You", user_message if user_message else f"[File: {user_file.name}]"))
                st.session_state.chat_history.append(("Assistant", bot_response))

            except Exception as e:
                st.error(f"Error communicating with backend: {e}")

# ----------------------------
# Display Chat History
# ----------------------------
if st.session_state.chat_history:
    st.subheader("💬 Conversation")
    for sender, text in st.session_state.chat_history:
        if sender == "You":
            st.markdown(f"**You:** {text}")
        else:
            st.markdown(f"**Assistant:** {text}")

# ----------------------------
# Floating Chatbox HTML/JS
# ----------------------------
# Convert the Python list to a JSON string
chat_history_json = json.dumps(st.session_state.chat_history)

chatbot_html = f"""
<style>
#chat-button {{
    position: fixed; bottom: 30px; right: 30px;
    width: 60px; height: 60px; border-radius: 50%;
    background-color: #4CAF50; color: white;
    font-size: 30px; text-align: center; line-height: 60px;
    cursor: pointer; z-index: 9999;
}}
#chat-box {{
    position: fixed; bottom: 100px; right: 30px;
    width: 400px; max-height: 500px;
    background-color: white; border: 1px solid #ccc; border-radius: 10px;
    padding: 10px; overflow-y: auto; box-shadow: 0px 0px 10px rgba(0,0,0,0.3);
    z-index: 9999; display: none; flex-direction: column;
    resize: both; min-width: 300px; min-height: 200px;
}}
#chat-header {{ font-weight: bold; font-size: 18px; margin-bottom: 5px; cursor: move; }}
#close-btn {{ float: right; cursor: pointer; color: red; }}
#chat-content {{ flex-grow: 1; overflow-y: auto; margin-bottom: 10px; padding: 5px; border: 1px solid #eee; border-radius: 5px; }}
#chat-input-container {{ display: flex; gap: 5px; }}
#chat-input {{ flex-grow: 1; padding: 8px; border-radius: 5px; border: 1px solid #ccc; }}
#send-btn {{ padding: 8px 12px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; }}
#file-input {{ padding: 5px; }}
#patient-id, #use-rag {{ margin-bottom: 5px; padding: 5px; }}
.message {{ margin: 5px 0; padding: 8px; border-radius: 10px; }}
.message.you {{ background-color: #e0f7fa; text-align: right; }}
.message.bot {{ background-color: #f0f0f0; text-align: left; }}
</style>

<div id="chat-button">💬</div>
<div id="chat-box">
    <div id="chat-header">Medical AI Assistant <span id="close-btn">✖</span></div>
    <div>
        <input type="text" id="patient-id" placeholder="Patient ID" value="001">
        <label><input type="checkbox" id="use-rag" checked> Use RAG</label>
    </div>
    <div id="chat-content"></div>
    <div id="chat-input-container">
        <input type="file" id="file-input" accept=".pdf,.png,.jpg,.jpeg">
        <input type="text" id="chat-input" placeholder="Type your message...">
        <button id="send-btn">Send</button>
    </div>
</div>

<script>
const chatButton = document.getElementById("chat-button");
const chatBox = document.getElementById("chat-box");
const closeBtn = document.getElementById("close-btn");
const chatContent = document.getElementById("chat-content");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const fileInput = document.getElementById("file-input");
const patientIdInput = document.getElementById("patient-id");
const useRagInput = document.getElementById("use-rag");

window.onload = () => {{
    const history = JSON.parse('{chat_history_json}');
    history.forEach(item => {{
        const div = document.createElement("div");
        div.className = `message ${{item[0].toLowerCase()}}`;
        div.innerHTML = `<strong>${{item[0]}}:</strong> ${{item[1]}}`;
        chatContent.appendChild(div);
    }});
    chatContent.scrollTop = chatContent.scrollHeight;
}};

chatButton.onclick = () => {{ chatBox.style.display = "flex"; chatButton.style.display = "none"; }};
closeBtn.onclick = () => {{ chatBox.style.display = "none"; chatButton.style.display = "flex"; }};

function appendMessage(sender, message) {{
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${{sender.toLowerCase()}}`;
    msgDiv.innerHTML = `<strong>${{sender}}:</strong> ${{message}}`;
    chatContent.appendChild(msgDiv);
    chatContent.scrollTop = chatContent.scrollHeight;
}}

sendBtn.onclick = async () => {{
    const message = chatInput.value.trim();
    const file = fileInput.files.length > 0 ? fileInput.files[0] : null;
    const patient_id = patientIdInput.value.trim() || "001";
    const use_rag = useRagInput.checked;

    if (!message && !file) return;

    appendMessage("You", message ? message : (file ? `[File: ${{file.name}}]` : ""));
    chatInput.value = "";
    fileInput.value = "";

    const formData = new FormData();
    formData.append("patient_id", patient_id);
    formData.append("message", message);
    formData.append("use_rag", use_rag);
    if (file) formData.append("file", file);

    try {{
        const response = await fetch("{BASE_URL}/chat_with_file", {{
            method: "POST",
            body: formData
        }});
        const data = await response.json();
        appendMessage("Assistant", data.response || "No response from bot");
    }} catch (error) {{
        appendMessage("Assistant", "Error: " + error);
    }}
}};

// Draggable chatbox
let offsetX=0, offsetY=0, isDown=false;
const chatHeader = document.getElementById("chat-header");
chatHeader.onmousedown = (e) => {{
    isDown = true;
    offsetX = chatBox.offsetLeft - e.clientX;
    offsetY = chatBox.offsetTop - e.clientY;
}};
document.onmouseup = () => isDown=false;
document.onmousemove = (e) => {{
    if (!isDown) return;
    chatBox.style.left = (e.clientX + offsetX) + "px";
    chatBox.style.top = (e.clientY + offsetY) + "px";
}};
</script>
"""

components.html(chatbot_html, height=600, width=500)