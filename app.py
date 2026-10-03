from pathlib import Path
import traceback
import uvicorn

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import json

from backend import run_travel_agent, get_database_url
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import psycopg
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres import PostgresSaver



# This is to allow nested event loops for async calls in FastAPI
import nest_asyncio
nest_asyncio.apply()

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="AI Travel Planning System",
    description="LamgGraph Multi-Agent Travel Planner with FastAPI Frontend",
    version="1.0.0"
)

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static"
)

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
) 

# Database connection for conversation history
def get_db_conn():
    return psycopg.connect(get_database_url(), autocommit=True, row_factory=dict_row)


MESSAGE_TYPE_MAP = {
    "HumanMessage": "human",
    "AIMessage": "ai",
    "SystemMessage": "system",
}


def _serialize_message(msg):
    msg_type = type(msg).__name__
    role = MESSAGE_TYPE_MAP.get(msg_type, "ai")
    return {"type": msg_type, "role": role, "content": msg.content}


class TravelRequest(BaseModel):
    message: str
    thread_id: str | None = None


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )

@app.post("/api/travel")
async def travel_planner(request_data: TravelRequest):
    try:
        user_message = request_data.message.strip()

        if not user_message:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Message cannot be empty"
                }
            )

        result = run_travel_agent(user_message, request_data.thread_id)

        return JSONResponse(
            content={
                "success": True,
                "thread_id": result["thread_id"],
                "answer": result["answer"],
                "flight_results": result["flight_results"],
                "hotel_results": result["hotel_results"],
                "itinerary": result["itinerary"],
                "llm_calls": result["llm_calls"],
            }
        )

    except Exception as e:
        print("ERROR: ", e)
        traceback.print_exc()

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "message": "AI Travel Planner API is running"
    }


@app.get("/api/conversations")
async def list_conversations():
    """List all conversations from the database."""
    try:
        conn = get_db_conn()
        try:
            with conn.cursor() as cur:
                # Get distinct threads with their latest checkpoint
                cur.execute("""
                    SELECT DISTINCT ON (c.thread_id)
                        c.thread_id,
                        c.checkpoint_id,
                        c.metadata
                    FROM checkpoints c
                    WHERE c.checkpoint_ns = ''
                    ORDER BY c.thread_id, c.checkpoint_id DESC
                """)
                rows = cur.fetchall()

            # Now load each thread's full state to get user_query and final answer
            checkpointer = PostgresSaver(conn)
            conversations = []

            for row in rows:
                thread_id = row["thread_id"]
                config = {"configurable": {"thread_id": thread_id}}
                state = checkpointer.get(config)

                if not state:
                    continue

                channel_values = state.get("channel_values", {})
                user_query = channel_values.get("user_query", "")
                messages = channel_values.get("messages", [])

                # Get the last AI message as the answer
                answer = ""
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage) and msg.content:
                        answer = msg.content
                        break

                if not user_query and messages:
                    for msg in messages:
                        if isinstance(msg, HumanMessage):
                            user_query = msg.content
                            break

                conversations.append({
                    "thread_id": thread_id,
                    "title": user_query[:100] if user_query else thread_id,
                    "user_query": user_query,
                    "answer": answer[:500] if answer else "",
                    "flight_results": channel_values.get("flight_results", ""),
                    "hotel_results": channel_values.get("hotel_results", ""),
                    "itinerary": channel_values.get("itinerary", ""),
                    "llm_calls": channel_values.get("llm_calls", 0),
                    "ts": str(state.get("ts", "")),
                    "messages": [_serialize_message(m) for m in messages],
                })

            # Sort by timestamp descending (most recent first)
            conversations.sort(key=lambda x: x["ts"], reverse=True)

            return JSONResponse(content={
                "success": True,
                "conversations": conversations,
            })

        finally:
            conn.close()

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.get("/api/conversations/{thread_id}")
async def get_conversation(thread_id: str):
    """Load a specific conversation by thread_id."""
    try:
        conn = get_db_conn()
        try:
            checkpointer = PostgresSaver(conn)
            config = {"configurable": {"thread_id": thread_id}}
            state = checkpointer.get(config)

            if not state:
                return JSONResponse(
                    status_code=404,
                    content={"success": False, "error": "Conversation not found"}
                )

            channel_values = state.get("channel_values", {})
            messages = channel_values.get("messages", [])
            user_query = channel_values.get("user_query", "")

            answer = ""
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.content:
                    answer = msg.content
                    break

            return JSONResponse(content={
                "success": True,
                "thread_id": thread_id,
                "title": user_query[:100] if user_query else thread_id,
                "user_query": user_query,
                "answer": answer,
                "flight_results": channel_values.get("flight_results", ""),
                "hotel_results": channel_values.get("hotel_results", ""),
                "itinerary": channel_values.get("itinerary", ""),
                "llm_calls": channel_values.get("llm_calls", 0),
                "ts": str(state.get("ts", "")),
                "messages": [_serialize_message(m) for m in messages],
            })

        finally:
            conn.close()

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.get("/favicon.ico")
async def favicon():
    return JSONResponse(content={})


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )

