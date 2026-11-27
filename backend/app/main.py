import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import account, admin, devices, student, teacher

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
settings = get_settings()

app = FastAPI(title="Aprende Multiagente API", version="1.0.0", description="Sistema multiagente para personalizar contenido pedagógico en primaria.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(account.router)
app.include_router(admin.router)
app.include_router(teacher.router)
app.include_router(student.router)
app.include_router(devices.router)


@app.get("/health")
def health():
    # Solo indica si cada integración está configurada; nunca expone valores
    return {"status": "ok", "gemini": bool(settings.gemini_api_key), "model": settings.gemini_model, "auth": bool(settings.supabase_url and settings.supabase_secret_key)}
