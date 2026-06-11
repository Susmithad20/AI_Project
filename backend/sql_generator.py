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


# Per-dialect syntax guidance injected into the system prompt.
_DIALECTS = {
    "mssql": {
        "name": "Microsoft SQL Server (T-SQL)",
        "syntax": "Use T-SQL syntax (e.g. TOP instead of LIMIT, GETDATE() for current time).",
        "cap": "Always cap rows with `SELECT TOP ({max_rows}) ...`",
    },
    "sqlite": {
        "name": "SQLite",
        "syntax": "Use SQLite syntax (LIMIT instead of TOP, date('now') for current time).",
        "cap": "Always cap rows with a trailing `LIMIT {max_rows}`",
    },
}

SYSTEM_PROMPT = """You are a senior data analyst that writes {dialect_name} queries.

You are given:
1. A database SCHEMA.
2. An EMAIL from a customer describing the data they want.

Your job: produce ONE single read-only SQL SELECT query that answers the email.

Hard rules:
- ONLY a SELECT statement (or a WITH ... SELECT CTE). Never INSERT, UPDATE, DELETE,
  MERGE, DROP, ALTER, CREATE, TRUNCATE, GRANT, EXEC or any data-modifying statement.
- Use only tables and columns that exist in the provided SCHEMA.
- {dialect_syntax}
- {dialect_cap} unless the email clearly asks for a single aggregate value.
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


def generate_sql(email: str, schema: str, max_rows: int = 200, dialect: str = "sqlite") -> str:
    """Generate a read-only SELECT query from an email + schema for `dialect`."""
    client = _get_client()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    d = _DIALECTS.get(dialect, _DIALECTS["sqlite"])
    system_prompt = SYSTEM_PROMPT.format(
        dialect_name=d["name"],
        dialect_syntax=d["syntax"],
        dialect_cap=d["cap"].format(max_rows=max_rows),
    )

    user_prompt = (
        f"SCHEMA:\n{schema.strip()}\n\n"
        f"EMAIL:\n{email.strip()}\n\n"
        "Write the SQL query now."
    )

    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    sql = resp.choices[0].message.content or ""
    return _strip_code_fences(sql)
