"""
report_generator.py
Turns raw query results into a short, human-friendly summary for the chat.
Uses OpenAI for a natural-language answer, with a plain fallback if the
API call fails. No document is generated (POC scope = reply in chat).
"""
import os
from openai import OpenAI

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def _rows_to_text(columns, rows, limit: int = 50) -> str:
    header = " | ".join(str(c) for c in columns)
    lines = [header, "-" * len(header)]
    for r in rows[:limit]:
        lines.append(" | ".join("" if v is None else str(v) for v in r))
    if len(rows) > limit:
        lines.append(f"... ({len(rows) - limit} more rows)")
    return "\n".join(lines)


def summarize(email: str, columns, rows) -> str:
    """Return a short natural-language summary answering the original email."""
    table_text = _rows_to_text(columns, rows)
    if not rows:
        return "The query ran successfully but returned no rows."

    try:
        client = _get_client()
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        resp = client.chat.completions.create(
            model=model,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a data analyst replying to a customer's request. "
                        "Given their email and the query results, write a brief, "
                        "professional 2-4 sentence summary of what the data shows. "
                        "Do not invent numbers; only use the provided rows."
                    ),
                },
                {
                    "role": "user",
                    "content": f"EMAIL:\n{email.strip()}\n\nRESULTS:\n{table_text}",
                },
            ],
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        # Fallback: no LLM summary, just acknowledge the row count.
        return f"Query returned {len(rows)} row(s)."
