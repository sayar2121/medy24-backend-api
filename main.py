from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes.auth.patho_lab_user_routes import router as patho_lab_router
from routes.lab_test.core_test_routes import router as core_test_router
from routes.lab_test.lab_test_inventory_routes import router as lab_test_inventory_router
from routes.lab_test.test_packaage_routes import router as test_package_router
from routes.about_us.about_us_routes import router as about_us_router
from db import init_db
import uvicorn
import os

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    init_db()
    print("🚀 Medy24 Backend is starting up...")
    print("🔗 Documentation available at http://localhost:8000/docs")
    yield
    # Shutdown logic (if any)

app = FastAPI(
    title="Medy24 Backend", 
    description="Backend for Patho Lab Management",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if not exists
os.makedirs("uploads/auth", exist_ok=True)
os.makedirs("uploads/lab_tests", exist_ok=True)
os.makedirs("uploads/about_us", exist_ok=True)

# Mount static files for uploads
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
async def root():
    return {
        "message": "Welcome to Medy24 Patho Lab API",
        "docs": "/docs",
        "health": "/health"
    }

# Register routers
app.include_router(patho_lab_router)
app.include_router(core_test_router)
app.include_router(lab_test_inventory_router)
app.include_router(test_package_router)
app.include_router(about_us_router)

if __name__ == "__main__":
    # Running on 0.0.0.0 to make it accessible on all network interfaces
    uvicorn.run(app, host="0.0.0.0", port=8000)
