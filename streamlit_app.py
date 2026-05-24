from pathlib import Path
import streamlit as st
import requests
import inngest

st.set_page_config(page_title="RAG Assistant", page_icon="🤖", layout="wide")

FASTAPI_URL = "https://your-app.onrender.com"


def save_pdf(file) -> Path:
    folder = Path("uploads")
    folder.mkdir(exist_ok=True)

    path = folder / file.name
    path.write_bytes(file.getbuffer())
    return path


def list_pdfs():
    folder = Path("uploads")
    if not folder.exists():
        return []
    return [f.name for f in folder.glob("*.pdf")]


def send_ingest_event(pdf_path: Path):
    client = inngest.Inngest(app_id="rag_app", is_production=False)

    return client.send(
        inngest.Event(
            name="rag/ingest_pdf",
            data={
                "pdf_path": str(pdf_path.resolve()),
                "source_id": pdf_path.name
            }
        )
    )



st.title("📄 RAG Assistant")

col1, col2 = st.columns(2)



with col1:
    st.subheader("Upload PDF")

    file = st.file_uploader("Choose PDF", type=["pdf"])

    if file and st.button("Ingest PDF"):
        path = save_pdf(file)
        send_ingest_event(path)
        st.success(f"Sent for processing: {path.name}")



with col2:
    st.subheader("Ask Questions")

    files = list_pdfs()
    selected = st.selectbox("Select PDF", files)

    question = st.text_input("Your question")
    top_k = st.slider("Top K", 1, 10, 5)

    if st.button("Ask"):

        if not selected:
            st.error("Please select a PDF first")
            st.stop()

        if not question.strip():
            st.error("Enter a question")
            st.stop()

        payload = {
            "question": question,
            "top_k": top_k,
            "source_filter": selected
        }

        with st.spinner("Thinking..."):

            try:
                res = requests.post(
                    f"{FASTAPI_URL}/query",
                    json=payload,
                    timeout=120
                )

                data = res.json()

                if res.status_code != 200:
                    st.error(data)
                    st.stop()

            except Exception as e:
                st.error(f"Backend error: {e}")
                st.stop()

        st.success("Answer ready!")

        st.markdown("### 🤖 Answer")
        st.write(data.get("answer", ""))

        if data.get("sources"):
            st.markdown("### 📚 Sources")
            for s in data["sources"]:
                st.write(f"- {s}")