# Email → SQL → Report POC

A simplified proof-of-concept that automates the daily workflow:

> A customer emails a data request → you write a SQL query → run it on Microsoft
> SQL Server → send the results back.

Here, you paste the email into a **chat UI**. The system:

1. **sql-generator** — uses OpenAI to turn the email + schema into a **read-only**
   T-SQL `SELECT`.
2. **sql-executor** — validates the query is read-only, then runs it on Microsoft
   SQL Server (or returns mock rows until your DB is connected).
3. **report-generator** — summarizes the results in plain English and shows the
   table back in the chat. (No document export in this POC — reply in chat only.)

```
React chat  ──POST /api/chat──►  FastAPI backend
                                   ├─ sql_generator.py   (OpenAI)
                                   ├─ sql_executor.py    (read-only guard + pyodbc → MSSQL)
                                   └─ report_generator.py (OpenAI summary)
```

> Note on the "Express API": the request asked to connect the chat to the backend
> with an Express API. For a single-language, simpler POC this uses **FastAPI**
> (Python) as the HTTP API directly — it plays the same role as Express and keeps
> everything in one backend. The React dev server proxies `/api/*` to it.

---

## Project layout

```
AI_Project/
├── backend/
│   ├── main.py              # FastAPI app, wires the 3 components
│   ├── sql_generator.py     # email + schema -> SQL (OpenAI)
│   ├── sql_executor.py      # read-only validation + MSSQL execution
│   ├── report_generator.py  # results -> chat summary (OpenAI)
│   ├── schema_example.sql   # sample schema to paste into the UI
│   ├── requirements.txt
│   └── .env.example
└── frontend/                # React + Vite chat interface
    └── src/App.jsx
```

---

## 1. Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # then edit .env
```

Edit `backend/.env`:

- Set `OPENAI_API_KEY`.
- Leave `USE_MOCK_DB=true` to try it without a database.
- Set `USE_MOCK_DB=false` and fill the `MSSQL_*` values once your DB is ready.

Run it:

```bash
uvicorn main:app --reload --port 8000
```

Health check: <http://localhost:8000/api/health>

## 2. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Paste the schema (left panel) and an email
(bottom box) and hit **Send**.

---

## 3. Connecting to Microsoft SQL Server

The executor uses **pyodbc** + the Microsoft ODBC driver.

### a) Install the ODBC driver

- **Windows:** download "ODBC Driver 18 for SQL Server" from Microsoft.
- **macOS:** `brew tap microsoft/mssql-release && brew install msodbcsql18`
- **Ubuntu/Debian:**
  ```bash
  curl https://packages.microsoft.com/keys/microsoft.asc | sudo tee /etc/apt/trusted.gpg.d/microsoft.asc
  curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list
  sudo apt-get update
  sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev
  ```

### b) Create a READ-ONLY database user (defense in depth)

Even though the app validates queries, enforce read-only at the DB level too:

```sql
CREATE LOGIN readonly_user WITH PASSWORD = 'StrongPassword!';
USE YourDatabase;
CREATE USER readonly_user FOR LOGIN readonly_user;
ALTER ROLE db_datareader ADD MEMBER readonly_user;   -- SELECT only, no writes
```

### c) Fill in `.env`

```env
USE_MOCK_DB=false
MSSQL_SERVER=your-server.database.windows.net   # or localhost
MSSQL_PORT=1433
MSSQL_DATABASE=YourDatabase
MSSQL_USER=readonly_user
MSSQL_PASSWORD=StrongPassword!
MSSQL_DRIVER=ODBC Driver 18 for SQL Server
MSSQL_TRUST_CERT=yes        # "no" if the server has a trusted certificate
```

### d) Restart the backend

```bash
uvicorn main:app --reload --port 8000
```

That's it — queries now run against your real database.

---

## Safety: how "read-only" is enforced

`sql_executor.validate_read_only()` rejects a query unless it:

- starts with `SELECT` (or a `WITH … SELECT` CTE),
- contains **no** forbidden keywords (`INSERT`, `UPDATE`, `DELETE`, `MERGE`,
  `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `EXEC`, `INTO`, `GRANT`, …),
- contains no stacked statements (no mid-query `;`),
- comments are stripped first so they can't hide keywords.

The connection also requests `ApplicationIntent=ReadOnly`, and the recommended
DB user only has `db_datareader`. Three layers, so a bad query is blocked even
if one layer is bypassed.

---

## Next steps (beyond POC)

- Auto-read the inbox (IMAP / Microsoft Graph) instead of pasting emails.
- Generate a real report document (Excel/PDF) and email it back.
- Add per-customer schema selection and query history.
