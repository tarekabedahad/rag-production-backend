import streamlit as st
import inngest
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()
st.set_page_config(page_title="RAG Assistant", page_icon="🤖", layout="wide")


@st.cache_resource
def get_inngest_client() -> inngest.Inngest:
    return inngest.Inngest(
        app_id="rag_app",
        is_production=True,
        event_key=os.getenv("INNGEST_EVENT_KEY")
    )


def save_uploaded_pdf(file) -> Path:
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_path = uploads_dir / file.name
    file_path.write_bytes(file.getbuffer())
    return file_path



def trigger_inngest_event(event_name: str, data: dict):
    client = get_inngest_client()

    ids = client.send_sync(inngest.Event(name=event_name, data=data))
    return ids[0]


st.title("📄 RAG Production Dashboard")
st.markdown("---")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📤 Upload Document")
    uploaded = st.file_uploader("Select a PDF", type=["pdf"])
    if uploaded and st.button("Ingest File", type="primary"):
        with st.spinner("Processing..."):
            path = save_uploaded_pdf(uploaded)
            event_id = trigger_inngest_event("rag/ingest_pdf", {
                "pdf_path": str(path.resolve()),
                "source_id": path.name
            })
        st.success(f"Ingestion triggered! ID: {event_id}")

with col2:
    st.subheader("🔍 Ask a Question")
    with st.form("rag_query_form", clear_on_submit=False):
        question = st.text_input("Enter your query:", placeholder="e.g., How do I start the device?")
        top_k = st.slider("Retrieval Depth", 1, 10, 5)
        submitted = st.form_submit_button("Submit Question")

        if submitted and question.strip():
            with st.spinner("Submitting to knowledge base..."):
                event_id = trigger_inngest_event("rag/query_pdf_ai", {
                    "question": question.strip(),
                    "top_k": int(top_k)
                })

            st.success("Query submitted successfully!")
            st.info(f"Tracking ID: `{event_id}`")
            st.markdown(
                "Check the [Inngest Dashboard](https://app.inngest.com/) to monitor the progress of your query.")