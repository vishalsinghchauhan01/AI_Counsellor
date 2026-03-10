from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import chat, voice, colleges, user

load_dotenv()

app = FastAPI(title="AI Counsellor API", version="1.0.0")

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


@app.get("/")
def root():
    return {"status": "AI Counsellor API is running", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}
