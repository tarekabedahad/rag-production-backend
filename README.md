# RAG PDF Assistant

This is an AI-powered assistant that lets you talk to your PDFs. It ensures the AI answers your questions using **only** the information found in your specific documents.

## Why I built this
Standard AI chatbots often struggle when you give them multiple documents—they can mix up information or "hallucinate" (make up) facts. I built this system to solve three main problems:
* **Accuracy:** Using **LlamaIndex** and **Qdrant**, the AI is "grounded" in your documents, making answers more reliable.
* **Organization:** The system uses metadata filtering to keep your files separate and organized.
* **Reliability:** By using **Inngest**, heavy tasks (like processing large PDFs) run in the background, so the app stays fast and doesn't freeze.



## Tech Stack
- **Python** & **FastAPI**
- **LlamaIndex** (Data framework)
- **Inngest** (Background task orchestration)
- **Qdrant** (Vector database)
- **Docker** (Containerization)
- **Streamlit** (User Interface)

## How to run it
1. Make sure **Docker Desktop** is running.
2. Install the requirements:
   ```bash
   pip install -r requirements.txt
3. Create a .env file in the root folder and add your API key:
    ```bash
   OPENAI_API_KEY=your_openai_key_here
4. Start the backend:
    ```bash
   uvicorn main:app --reload
5. Start the frontend:
    ```bash
    streamlit run streamlit_app.py
**Built for speed, accuracy, and scale. Boom.**