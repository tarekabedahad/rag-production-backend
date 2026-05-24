from fastapi import FastAPI
import inngest
import inngest.fast_api

client = inngest.Inngest(app_id="rag_app")


@inngest.create_function(
    {"id": "query-pdf-ai", "name": "Query PDF AI"},
    {"event": "rag/query_pdf_ai"},
)
async def query_pdf_ai_function(ctx: inngest.Context, step: inngest.Step) -> str:
    question = ctx.event.data.get("question")
    return f"AI processed your question: {question}"


app = FastAPI()
inngest.fast_api.serve(app, client, [query_pdf_ai_function])
