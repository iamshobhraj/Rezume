"""FastAPI application entry point – lifespan, CORS, router mounts, and seeding."""

import json
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import LLMProvider, ResumeConfig  # noqa: F401 – ensures models are registered

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


def _seed_default_provider(db) -> None:
    """Migrate existing google providers and seed default if empty."""
    # Migrate ALL existing google providers to new models
    providers = db.query(LLMProvider).filter(LLMProvider.provider_type == "google").all()
    for provider in providers:
        if provider.chat_model in ("gemini-2.0-flash", "gemini-2.5-flash"):
            provider.chat_model = "gemma-4-31b-it"
            logger.info(f"Updated Google chat model to gemma-4-31b-it for '{provider.name}'")
        if provider.embedding_model == "models/text-embedding-004":
            provider.embedding_model = "gemini-embedding-2"
            provider.embedding_dim = 768
            logger.info(f"Updated Google embedding model to gemini-embedding-2 for '{provider.name}'")

    # Check if any provider at all exists before deciding to seed a new one
    existing = db.query(LLMProvider).first()
    if existing is not None:
        return

    if not settings.google_api_key:
        logger.warning(
            "No GOOGLE_API_KEY set in .env and no providers exist. "
            "Add a provider via the API or set GOOGLE_API_KEY."
        )
        return

    provider = LLMProvider(
        id=str(uuid.uuid4()),
        name="Google AI Studio (Default)",
        provider_type="google",
        base_url=None,
        api_key=settings.google_api_key,
        chat_model="gemma-4-31b-it",
        embedding_model="gemini-embedding-2",
        embedding_dim=768,
        is_active_chat=True,
        is_active_embedding=True,
    )
    db.add(provider)
    logger.info("Seeded default Google AI Studio provider")


def _seed_default_config(db) -> None:
    """Seed the default resume config if it doesn't exist."""
    existing = db.query(ResumeConfig).get("default")
    if existing is not None:
        return

    # Get the default provider ID for config references
    default_provider = db.query(LLMProvider).filter(LLMProvider.is_active_chat.is_(True)).first()
    provider_id = default_provider.id if default_provider else None

    config_data = {
        "target_role": "Software Engineer",
        "years_experience": 5,
        "skills_emphasis": [],
        "tone": "professional",
        "active_chat_provider_id": provider_id,
        "active_embedding_provider_id": provider_id,
    }

    config = ResumeConfig(
        id="default",
        config_json=json.dumps(config_data),
    )
    db.add(config)
    logger.info("Seeded default resume configuration")


def _seed_default_profile(db) -> None:
    """Seed the default user profile if it doesn't exist."""
    from app.models.user_profile import UserProfile
    existing = db.query(UserProfile).first()
    if existing is not None:
        return

    profile = UserProfile(
        id=1,
        name="Candidate Name",
        email="email@example.com",
        phone="(555) 000-0000",
        github="github.com/candidate",
        linkedin="linkedin.com/in/candidate",
        location="City, State",
        college="University Name",
        degree="B.S. in Computer Science",
        graduation_year="2025",
        coursework="Data Structures, Algorithms, Software Engineering",
    )
    db.add(profile)
    logger.info("Seeded default user profile")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler – runs on startup and shutdown."""
    # Startup
    logger.info("Starting Resume Intelligence Engine...")

    # Create all database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")

    # Seed defaults
    db = SessionLocal()
    try:
        _seed_default_provider(db)
        _seed_default_config(db)
        _seed_default_profile(db)
        db.commit()
    finally:
        db.close()

    logger.info("Application ready")
    yield

    # Shutdown
    logger.info("Shutting down...")


# Create the FastAPI app
app = FastAPI(
    title="Resume Intelligence Engine",
    description="AI-powered resume generation with multi-provider LLM support",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS – allow the Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers under /api prefix
from app.routers import health, providers, projects, resumes, config, github, history, profile  # noqa: E402

app.include_router(health.router, prefix="/api")
app.include_router(providers.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(resumes.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(github.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(profile.router, prefix="/api")

