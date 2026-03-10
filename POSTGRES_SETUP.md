# Local PostgreSQL + pgvector setup for UttaraPath

The app uses **PostgreSQL** with the **pgvector** extension for vector search (instead of Pinecone). Everything runs locally.

---

## 1. Install PostgreSQL

- **Windows:** Download from [postgresql.org](https://www.postgresql.org/download/windows/) and run the installer. Remember the password you set for the `postgres` user.
- **macOS:** `brew install postgresql@16`
- **Linux:** `sudo apt install postgresql postgresql-contrib` (Ubuntu/Debian)

Start the PostgreSQL service so it’s running on `localhost:5432`.

---

## 2. Install pgvector extension

pgvector adds a `vector` type and similarity search to PostgreSQL.

- **Windows:** Use the installer from [pgvector releases](https://github.com/pgvector/pgvector/releases) or build from source.
- **macOS:** `brew install pgvector`
- **Linux:** Follow [pgvector install](https://github.com/pgvector/pgvector#installation).

Then enable the extension in your database (see step 3).

---

## 3. Create the database

In a terminal (or pgAdmin / any SQL client), connect as `postgres` and run:

```sql
CREATE DATABASE uttarapath;
\c uttarapath   -- connect to it (psql)
CREATE EXTENSION IF NOT EXISTS vector;
```

Or in one line with `psql`:

```bash
psql -U postgres -c "CREATE DATABASE uttarapath;"
psql -U postgres -d uttarapath -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

---

## 4. Set DATABASE_URL in backend .env

In `backend/.env`:

```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/uttarapath
```

Replace `YOUR_PASSWORD` with your PostgreSQL password. If your user or port is different, adjust the URL.

You can **remove** any Pinecone variables (`PINECONE_API_KEY`, `PINECONE_INDEX_NAME`); they are no longer used.

---

## 5. Run ingest (creates table and fills vectors)

From the backend folder (with your venv activated):

```bash
python rag/ingest.py
```

This will:

- Create the `uttarapath_vectors` table (with a `vector(1536)` column).
- Embed all data from `data/*.json` (OpenAI).
- Insert vectors into PostgreSQL.
- Optionally create an index for faster search.

After this, the chat uses **local PostgreSQL** for RAG instead of Pinecone.
