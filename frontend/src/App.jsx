import { useState } from "react";

const SAMPLE_EMAIL =
  "Hi team, could you send me the top 5 customers by total order value " +
  "for paid orders in 2026? Thanks!";

const SAMPLE_SCHEMA = `Table: customers
  - id (int, PK)
  - customer_name (nvarchar)
  - region (nvarchar)
  - created_at (datetime)

Table: orders
  - id (int, PK)
  - customer_id (int, FK -> customers.id)
  - order_total (decimal)
  - order_date (date)
  - status (nvarchar)  -- 'paid', 'pending', 'cancelled'`;

function ResultTable({ columns, rows }) {
  if (!columns || !rows) return null;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td key={j}>{cell === null ? "" : String(cell)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function App() {
  const [email, setEmail] = useState(SAMPLE_EMAIL);
  const [schema, setSchema] = useState(SAMPLE_SCHEMA);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  async function send() {
    if (!email.trim() || loading) return;
    setLoading(true);
    setMessages((m) => [...m, { role: "user", text: email }]);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, schema_text: schema }),
      });
      const data = await res.json();
      setMessages((m) => [...m, { role: "assistant", data }]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "assistant", data: { error: String(e) } },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header>
        <h1>📧 → 🛢️ Email-to-SQL Assistant</h1>
        <p>Paste a customer email, get an auto-generated read-only query + results.</p>
      </header>

      <div className="layout">
        <aside className="schema-panel">
          <label>Database schema (file content or description)</label>
          <textarea
            value={schema}
            onChange={(e) => setSchema(e.target.value)}
            rows={16}
          />
        </aside>

        <main className="chat">
          <div className="messages">
            {messages.length === 0 && (
              <div className="empty">Paste an email below and hit Send.</div>
            )}
            {messages.map((msg, i) =>
              msg.role === "user" ? (
                <div key={i} className="bubble user">
                  {msg.text}
                </div>
              ) : (
                <div key={i} className="bubble assistant">
                  {msg.data.error && (
                    <div className="error">⚠️ {msg.data.error}</div>
                  )}
                  {msg.data.summary && (
                    <p className="summary">{msg.data.summary}</p>
                  )}
                  {msg.data.sql && (
                    <details open>
                      <summary>Generated SQL</summary>
                      <pre>{msg.data.sql}</pre>
                    </details>
                  )}
                  <ResultTable
                    columns={msg.data.columns}
                    rows={msg.data.rows}
                  />
                </div>
              )
            )}
            {loading && <div className="bubble assistant">Thinking…</div>}
          </div>

          <div className="composer">
            <textarea
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Paste the customer email here…"
              rows={4}
            />
            <button onClick={send} disabled={loading}>
              {loading ? "…" : "Send"}
            </button>
          </div>
        </main>
      </div>
    </div>
  );
}
