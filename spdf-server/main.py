"""
SPDF Server - FastAPI Application

Main application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pathlib import Path
from database import engine, Base
from routes import auth, keys, documents, admin, license_auth

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="SPDF Server",
    description="Secure Portable Document Format Server API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(license_auth.router)  # License key authentication
app.include_router(keys.router)
app.include_router(documents.router)
app.include_router(admin.router)

# Static files for admin dashboard
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
def root():
    return RedirectResponse(url="/login.html")


@app.get("/login.html")
def login_page():
    from fastapi.responses import FileResponse
    return FileResponse(static_dir / "login.html")


@app.get("/admin.html")
def admin_page():
    from fastapi.responses import FileResponse
    return FileResponse(static_dir / "admin.html")


@app.get("/health")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

