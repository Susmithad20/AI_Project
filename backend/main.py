"""
main.py — FastAPI backend that ties the three components together:

    email + schema  ->  sql_generator  ->  sql_executor  ->  report_generator

Run:  uvicorn main:app --reload --port 8000
"""
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import sql_generator
import sql_executor
import report_generator

load_dotenv()

app = FastAPI(title="Email-to-SQL POC")

# Allow the React dev server to call us.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# A small default schema so the POC works out of the box. Replace via the UI
# or by editing schema_example.sql.
DEFAULT_SCHEMA = """
Table: customers
  - id (int, PK)
  - customer_name (nvarchar)
  - region (nvarchar)
  - created_at (datetime)

Table: orders
  - id (int, PK)
  - customer_id (int, FK -> customers.id)
  - order_total (decimal)
  - order_date (date)
  - status (nvarchar)  -- 'paid', 'pending', 'cancelled'
""".strip()


class ChatRequest(BaseModel):
    email: str
    schema_text: str | None = None


class ChatResponse(BaseModel):
    sql: str | None = None
    columns: list | None = None
    rows: list | None = None
    summary: str | None = None
    error: str | None = None


@app.get("/api/health")
def health():
    return {"status": "ok", "mock_db": os.getenv("USE_MOCK_DB", "true")}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    max_rows = int(os.getenv("MAX_ROWS", "200"))
    schema = (req.schema_text or "").strip() or DEFAULT_SCHEMA

    # 1) Generate SQL from the email.
    try:
        sql = sql_generator.generate_sql(req.email, schema, max_rows=max_rows)
    except Exception as e:
        return ChatResponse(error=f"SQL generation failed: {e}")

    # 2) Validate (read-only) + execute.
    try:
        columns, rows = sql_executor.run_query(sql, max_rows=max_rows)
    except sql_executor.UnsafeQueryError as e:
        return ChatResponse(sql=sql, error=f"Blocked unsafe query: {e}")
    except Exception as e:
        return ChatResponse(sql=sql, error=f"Query execution failed: {e}")

    # 3) Summarize results for the chat.
    summary = report_generator.summarize(req.email, columns, rows)

    return ChatResponse(sql=sql, columns=columns, rows=rows, summary=summary)
