"""
sql_generator.py
Turns a plain-English customer email + a database schema into a single
read-only SQL SELECT statement using OpenAI.
"""
import os
import re
from openai import OpenAI

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Add it to backend/.env")
        _client = OpenAI(api_key=api_key)
    return _client


SYSTEM_PROMPT = """You are a senior data analyst that writes Microsoft SQL Server (T-SQL) queries.

You are given:
1. A database SCHEMA.
2. An EMAIL from a customer describing the data they want.

Your job: produce ONE single read-only SQL SELECT query that answers the email.

Hard rules:
- ONLY a SELECT statement (or a WITH ... SELECT CTE). Never INSERT, UPDATE, DELETE,
  MERGE, DROP, ALTER, CREATE, TRUNCATE, GRANT, EXEC or any data-modifying statement.
- Use only tables and columns that exist in the provided SCHEMA.
- Use T-SQL syntax (e.g. TOP instead of LIMIT, GETDATE() for current time).
- Always cap rows with `SELECT TOP (N) ...` (use N = {max_rows}) unless the email
  clearly asks for a single aggregate value.
- Do not invent columns. If the email is ambiguous, make a reasonable assumption.
- Return ONLY the SQL. No explanation, no markdown fences.
"""


def _strip_code_fences(text: str) -> str:
    """Remove ```sql ... ``` fences if the model added them."""
    text = text.strip()
    fence = re.match(r"^```(?:sql)?\s*(.*?)\s*```$", text, re.DOTALL | re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    return text


def generate_sql(email: str, schema: str, max_rows: int = 200) -> str:
    """Generate a read-only T-SQL SELECT query from an email + schema."""
    client = _get_client()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    user_prompt = (
        f"SCHEMA:\n{schema.strip()}\n\n"
        f"EMAIL:\n{email.strip()}\n\n"
        "Write the SQL query now."
    )

    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(max_rows=max_rows)},
            {"role": "user", "content": user_prompt},
        ],
    )
    sql = resp.choices[0].message.content or ""
    return _strip_code_fences(sql)
