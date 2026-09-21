import streamlit as st
from anthropic import Anthropic
from pypdf import PdfReader
from docx import Document
import io

# ----------------------------
# Page Config
# ----------------------------
st.set_page_config(
    page_title="Personal Document Chatbot",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Personal Document Chatbot")
st.caption("PDF, TXT ya DOCX upload karein — summary lein ya sawal poochein")

# ----------------------------
# Session State Initialization
# ----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "document_text" not in st.session_state:
    st.session_state.document_text = ""

if "document_name" not in st.session_state:
    st.session_state.document_name = ""


# ----------------------------
# Helper Functions
# ----------------------------
def extract_text_from_pdf(file_bytes):
    """Extract text from a PDF file."""
    reader = PdfReader(io.BytesIO(file_bytes))
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text.strip()


def extract_text_from_docx(file_bytes):
    """Extract text from a DOCX file."""
    doc = Document(io.BytesIO(file_bytes))
    text = "\n".join(para.text for para in doc.paragraphs if para.text.strip())
    return text.strip()


def extract_text_from_txt(file_bytes):
    """Extract text from a TXT file."""
    return file_bytes.decode("utf-8", errors="ignore").strip()


def extract_text(uploaded_file):
    """Route the uploaded file to the correct extractor based on its extension."""
    file_bytes = uploaded_file.read()
    name = uploaded_file.name.lower()

    if name.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif name.endswith(".docx"):
        return extract_text_from_docx(file_bytes)
    elif name.endswith(".txt"):
        return extract_text_from_txt(file_bytes)
    else:
        return None


def truncate_text(text, max_chars=150000):
    """Keep the document within a safe size for the model's context window."""
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n[Document truncated due to length...]"
    return text


def get_client(api_key):
    return Anthropic(api_key=api_key)


def call_claude(client, system_prompt, user_message, history=None):
    """Send a message to Claude and return the text response."""
    messages = []
    if history:
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1500,
        system=system_prompt,
        messages=messages
    )
    return response.content[0].text


# ----------------------------
# Sidebar: API Key + File Upload
# ----------------------------
with st.sidebar:
    st.header("⚙️ Settings")

    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        help="Apni Anthropic API key yahan daalein. Ye kahin save nahi hoti."
    )

    st.divider()

    st.header("📁 Document Upload")
    uploaded_file = st.file_uploader(
        "PDF, TXT, ya DOCX file upload karein",
        type=["pdf", "txt", "docx"]
    )

    if uploaded_file is not None:
        if uploaded_file.name != st.session_state.document_name:
            with st.spinner("Document padha ja raha hai..."):
                extracted = extract_text(uploaded_file)

                if extracted is None or extracted == "":
                    st.error("Is file se text nikal nahi saka. Doosri file try karein.")
                else:
                    st.session_state.document_text = truncate_text(extracted)
                    st.session_state.document_name = uploaded_file.name
                    st.session_state.messages = []  # naya document, purani chat clear
                    st.success(f"'{uploaded_file.name}' upload ho gaya! ✅")

    if st.session_state.document_text:
        st.info(f"📄 Active document: **{st.session_state.document_name}**")
        word_count = len(st.session_state.document_text.split())
        st.caption(f"Approx. {word_count} words loaded")

        if st.button("🗑️ Document Remove Karein"):
            st.session_state.document_text = ""
            st.session_state.document_name = ""
            st.session_state.messages = []
            st.rerun()

    st.divider()
    if st.button("🧹 Chat History Clear Karein"):
        st.session_state.messages = []
        st.rerun()


# ----------------------------
# Main Area
# ----------------------------
if not api_key:
    st.warning("👈 Shuru karne ke liye sidebar mein apni Anthropic API key daalein.")
    st.stop()

if not st.session_state.document_text:
    st.info("👈 Shuru karne ke liye sidebar se ek document (PDF/TXT/DOCX) upload karein.")
    st.stop()

client = get_client(api_key)

# System prompt with document content baked in
system_prompt = f"""Aap ek madadgar assistant hain jo user ke upload kiye gaye document ke bare mein sawalon ka jawab dete hain.

Neeche document ka poora content diya gaya hai. Sirf isi content ke hisaab se jawab dein. Agar jawab document mein nahi hai, to saaf bata dein ke ye information document mein maujood nahi hai — khud se mat banayein.

User jis language (Urdu/Roman Urdu/English/Hindi) mein baat kare, usi mein jawab dein.

--- DOCUMENT: {st.session_state.document_name} ---
{st.session_state.document_text}
--- DOCUMENT END ---
"""

# Quick action: Summarize button
col1, col2 = st.columns([1, 4])
with col1:
    if st.button("📝 Summarize Karein"):
        with st.spinner("Summary bana rahe hain..."):
            summary = call_claude(
                client,
                system_prompt,
                "Is document ka ek clear aur mukhtasar (concise) summary Roman Urdu ya Urdu mein dein, "
                "jisme main points bullet points mein hon."
            )
            st.session_state.messages.append({"role": "user", "content": "Document ki summary dein"})
            st.session_state.messages.append({"role": "assistant", "content": summary})
            st.rerun()

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
user_input = st.chat_input("Document ke bare mein kuch bhi poochein...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Soch raha hoon..."):
            try:
                answer = call_claude(
                    client,
                    system_prompt,
                    user_input,
                    history=st.session_state.messages[:-1]  # sab purane messages, current chhod kar
                )
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                error_msg = f"⚠️ Error aaya: {str(e)}"
                st.error(error_msg)
