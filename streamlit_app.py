import asyncio
from pathlib import Path
import streamlit as st
import inngest
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


async def send_rag_ingest_event(pdf_path: Path) -> None:
    client = get_inngest_client()
    await client.send(
        inngest.Event(
            name="rag/ingest_pdf",
            data={"pdf_path": str(pdf_path.resolve()), "source_id": pdf_path.name}
        )
    )


async def send_rag_query_event(question: str, top_k: int) -> str:
    client = get_inngest_client()
    response = await client.send(
        inngest.Event(
            name="rag/query_pdf_ai",
            data={"question": question, "top_k": top_k}
        )
    )
    return response.ids[0]


def run_inngest_event(coro):
    try:
        loop = asyncio.get_running_loop()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


st.title("📄 RAG Production Dashboard")
st.markdown("---")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📤 Upload Document")
    uploaded = st.file_uploader("Select a PDF", type=["pdf"])
    if uploaded and st.button("Ingest File", type="primary"):
        with st.spinner("Processing..."):
            path = save_uploaded_pdf(uploaded)
            run_inngest_event(send_rag_ingest_event(path))
        st.success(f"Added: {path.name}")

with col2:
    st.subheader("🔍 Ask a Question")
    with st.form("rag_query_form", clear_on_submit=False):
        question = st.text_input("Enter your query:", placeholder="e.g., How do I start the device?")
        top_k = st.slider("Retrieval Depth", 1, 10, 5)
        submitted = st.form_submit_button("Submit Question")

        if submitted and question.strip():
            with st.spinner("Submitting to knowledge base..."):
                event_id = run_inngest_event(send_rag_query_event(question.strip(), int(top_k)))

            st.success("Query submitted successfully!")
            st.info(f"Tracking ID: `{event_id}`")
            st.markdown(
                "Check the [Inngest Dashboard](https://app.inngest.com/) to monitor the progress of your query.")