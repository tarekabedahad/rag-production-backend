import logging
import uuid
import os
from fastapi import FastAPI, Request
import inngest
import inngest.fast_api
from inngest.experimental import ai
from dotenv import load_dotenv
from openai import OpenAI

from data_loader import load_and_chunk_pdf, embed_texts
from vector_db import QdrantStorage
from custom_type import RAGSearchResult, RAGUpsterResult, RAGChunkAndSrc

load_dotenv()

app = FastAPI()


inngest_client = inngest.Inngest(
    app_id="rag_app",
    logger=logging.getLogger("uvicorn"),
    is_production=False,
    serializer=inngest.PydanticSerializer()
)



@inngest_client.create_function(
    fn_id="RAG: Ingest PDF",
    trigger=inngest.TriggerEvent(event="rag/ingest_pdf")
)
async def rag_ingest_pdf(ctx: inngest.Context):

    def load_pdf(ctx):
        pdf_path = ctx.event.data["pdf_path"]
        source_id = ctx.event.data.get("source_id", pdf_path)

        chunks = load_and_chunk_pdf(pdf_path)
        return RAGChunkAndSrc(chunks=chunks, source_id=source_id)

    def upsert_vectors(data: RAGChunkAndSrc):
        vectors = embed_texts(data.chunks)

        ids = [
            str(uuid.uuid5(uuid.NAMESPACE_URL, f"{data.source_id}:{i}"))
            for i in range(len(data.chunks))
        ]

        payloads = [
            {"source": data.source_id, "text": data.chunks[i]}
            for i in range(len(data.chunks))
        ]

        QdrantStorage().upsert(ids, vectors, payloads)

        return RAGUpsterResult(ingested=len(data.chunks))

    chunks = await ctx.step.run(
        "load-pdf",
        lambda: load_pdf(ctx),
        output_type=RAGChunkAndSrc
    )

    result = await ctx.step.run(
        "upsert-vectors",
        lambda: upsert_vectors(chunks),
        output_type=RAGUpsterResult
    )

    return result.model_dump()


@app.post("/query")
async def query(request: Request):

    data = await request.json()

    question = data.get("question", "").strip()
    top_k = int(data.get("top_k", 5))
    source_filter = data.get("source_filter")

    if not question:
        return {"error": "Question is empty"}


    query_vec = embed_texts([question])[0]
    store = QdrantStorage()

    found = store.search(query_vec, top_k, source_filter=source_filter)

    contexts = found["contexts"] or []
    sources = found["sources"] or []

    context_block = "\n\n".join(contexts)


    prompt = f"""
Use ONLY the context below to answer.

Context:
{context_block}

Question:
{question}
"""


    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You must answer ONLY using the provided context."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=1024
    )

    answer = res.choices[0].message.content

    return {
        "answer": answer,
        "sources": sources
    }



@inngest_client.create_function(
    fn_id="RAG: Query PDF",
    trigger=inngest.TriggerEvent(event="rag/query_pdf_ai")
)
async def rag_query_pdf_ai(ctx: inngest.Context):

    question = ctx.event.data.get("question", "").strip()
    top_k = int(ctx.event.data.get("top_k", 5))
    source_filter = ctx.event.data.get("source_filter")

    query_vec = embed_texts([question])[0]
    store = QdrantStorage()

    found = store.search(query_vec, top_k, source_filter=source_filter)

    contexts = found["contexts"] or []
    sources = found["sources"] or []

    context_block = "\n\n".join(contexts)

    prompt = f"""
Context:
{context_block}

Question:
{question}
"""

    adapter = ai.openai.Adapter(
        auth_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o-mini"
    )

    res = await ctx.step.ai.infer(
        "llm-answer",
        adapter=adapter,
        body={
            "max_tokens": 1024,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": "Use only context."},
                {"role": "user", "content": prompt}
            ]
        }
    )

    answer = res["choices"][0]["message"]["content"]

    return {
        "answer": answer,
        "sources": sources,
        "num_contexts": len(contexts)
    }



inngest.fast_api.serve(
    app,
    inngest_client,
    functions=[rag_ingest_pdf, rag_query_pdf_ai]
)