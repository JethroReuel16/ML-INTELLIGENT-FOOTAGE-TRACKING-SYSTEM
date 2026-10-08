from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.search import router as search_router
from app.api.routes.results import router as results_router


app = FastAPI(
    title="VisionTrace AI API",
    description=(
        "Backend API for the VisionTrace AI "
        "image-guided video object retrieval system."
    ),
    version="1.0.0",
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Root
# ---------------------------------------------------------

@app.get("/")
def root():
    return {
        "name": "VisionTrace AI API",
        "version": "1.0.0",
        "status": "running",
        "message": "VisionTrace backend is running successfully.",
    }


# ---------------------------------------------------------
# Health
# ---------------------------------------------------------

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "visiontrace-backend",
    }


# ---------------------------------------------------------
# API Routes
# ---------------------------------------------------------

app.include_router(search_router)
app.include_router(results_router)