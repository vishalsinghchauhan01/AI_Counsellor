import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv
from routers import chat, voice, colleges, user, admin

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize PostgreSQL structured data tables
    from db.schema import init_tables, seed_from_json, is_table_empty
    from pathlib import Path

    init_tables()

    # Seed from JSON if tables are empty (first-run migration)
    data_dir = Path(__file__).resolve().parent.parent / "data"
    if is_table_empty("colleges"):
        seed_from_json(data_dir)

    yield


app = FastAPI(title="AI Counsellor API", version="1.0.0", lifespan=lifespan)

# Rate limiting — uses the limiter instance from chat router
app.state.limiter = chat.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])
app.include_router(colleges.router, prefix="/api/colleges", tags=["colleges"])
app.include_router(user.router, prefix="/api/user", tags=["user"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])


@app.get("/")
def root():
    return {"status": "AI Counsellor API is running", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}
