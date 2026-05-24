import streamlit as st
import inngest
import os

# Initialize client to send events
client = inngest.Inngest(
    app_id="rag_app",
    event_key=os.getenv("INNGEST_EVENT_KEY")
)

st.title("📄 RAG Production Dashboard")

if st.button("Submit Question"):
    # Simply fire the event. The "backend" (below) will catch it.
    client.send_sync(inngest.Event(
        name="rag/query_pdf_ai",
        data={"question": "How do I start the device?"}
    ))
    st.success("Task sent to background worker!")
    st.markdown("Monitor progress in your [Inngest Dashboard](https://app.inngest.com/).")