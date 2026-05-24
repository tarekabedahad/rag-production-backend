import asyncio
from pathlib import Path
import time
import streamlit as st
import inngest
from dotenv import load_dotenv
import os
import requests

load_dotenv()
st.set_page_config(page_title="RAG Assistant", page_icon="🤖", layout="wide")


@st.cache_resource
def get_inngest_client() -> inngest.Inngest:
    return inngest.Inngest(app_id="rag_app", is_production=False)


def save_uploaded_pdf(file) -> Path:
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_path = uploads_dir / file.name
    file_path.write_bytes(file.getbuffer())
    return file_path


async def send_rag_ingest_event(pdf_path: Path) -> None:
    client = get_inngest_client()
    await client.send(
        inngest.Event(name="rag/ingest_pdf", data={"pdf_path": str(pdf_path.resolve()), "source_id": pdf_path.name}))


async def send_rag_query_event(question: str, top_k: int) -> None:
    client = get_inngest_client()
    result = await client.send(inngest.Event(name="rag/query_pdf_ai", data={"question": question, "top_k": top_k}))
    return result[0]


def _inngest_api_base() -> str:
    return os.getenv("INNGEST_API_BASE", "http://127.0.0.1:8288/v1")


def fetch_runs(event_id: str) -> list[dict]:
    resp = requests.get(f"{_inngest_api_base()}/events/{event_id}/runs")
    resp.raise_for_status()
    return resp.json().get("data", [])


def wait_for_run_output(event_id: str, timeout_s: float = 120.0, poll_interval_s: float = 0.5) -> dict:
    start = time.time()
    while True:
        runs = fetch_runs(event_id)
        if runs:
            status = runs[0].get("status")
            if status in ("Completed", "Succeeded", "Success", "Finished"): return runs[0].get("output") or {}
            if status in ("Failed", "Cancelled"): raise RuntimeError(f"Run {status}")
        if time.time() - start > timeout_s: raise TimeoutError("Timed out.")
        time.sleep(poll_interval_s)


st.title("📄 RAG Production Dashboard")
st.markdown("---")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📤 Upload Document")
    uploaded = st.file_uploader("Select a PDF", type=["pdf"])
    if uploaded and st.button("Ingest File", type="primary"):
        with st.spinner("Processing..."):
            path = save_uploaded_pdf(uploaded)
            asyncio.run(send_rag_ingest_event(path))
            time.sleep(0.3)
        st.success(f"Added: {path.name}")

with col2:
    st.subheader("🔍 Ask a Question")
    with st.form("rag_query_form", clear_on_submit=False):
        question = st.text_input("Enter your query:", placeholder="e.g., How do I start the device?")
        top_k = st.slider("Retrieval Depth", 1, 10, 5, help="Number of context chunks to pull")
        submitted = st.form_submit_button("Submit Question")

        if submitted and question.strip():
            with st.spinner("Consulting knowledge base..."):
                event_id = asyncio.run(send_rag_query_event(question.strip(), int(top_k)))
                output = wait_for_run_output(event_id)
                answer = output.get("answer", "")
                sources = output.get("sources", [])

            st.success("Answer generated!")
            st.markdown(f"**AI Response:**\n\n{answer}")

            if sources:
                with st.expander("View Sources"):
                    for s in sources:
                        st.markdown(f"• `{s}`")
