from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from routes.auth.patho_lab_user_routes import router as patho_lab_router
from routes.auth.pharma_shop_user_routes import router as pharma_shop_router
from routes.lab_test.core_test_routes import router as core_test_router
from routes.lab_test.lab_test_inventory_routes import router as lab_test_inventory_router
from routes.lab_test.test_packaage_routes import router as test_package_router
from routes.lab_test.test_package_booking_routes import router as test_package_booking_router
from routes.about_us.about_us_routes import router as about_us_router
from routes.medicine.core_medicine_routes import router as medicine_router
from routes.terms_conditions.terms_conditions_routes import router as terms_conditions_router
from routes.privacy_policy.privacy_policy_routes import router as privacy_policy_router
from routes.auth.customer_user_routes import router as customer_router
from routes.cart.cart_routes import router as cart_router
from routes.medicine.medicine_order_websocket import router as medicine_order_ws_router
from db import init_db
import uvicorn
import os
from contextlib import asynccontextmanager

try:
    import firebase_admin
    from firebase_admin import credentials
except ImportError:
    firebase_admin = None
    credentials = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    init_db()
    
    # Initialize Firebase Admin SDK
    if firebase_admin and credentials:
        firebase_creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        if firebase_creds_path and os.path.exists(firebase_creds_path):
            try:
                cred = credentials.Certificate(firebase_creds_path)
                try:
                    firebase_admin.get_app()
                except ValueError:
                    # App doesn't exist yet, initialize it
                    firebase_admin.initialize_app(cred)
                print("✅ Firebase initialized successfully")
            except Exception as e:
                print(f"Firebase initialization warning: {e}")
        else:
            print("Firebase credentials path not found. Phone auth will be unavailable.")
    else:
        print("Firebase Admin SDK not installed.")
    
    print("Medy24 Backend is starting up...")
    print("Documentation available at http://localhost:8000/docs")
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

@app.get("/")
async def root():
    return {
        "message": "Welcome to Medy24 Patho Lab API",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    favicon_path = os.path.join(os.path.dirname(__file__), "static", "medy24_logo.svg")
    print(f"🔍 Favicon request received. Path: {favicon_path}")
    print(f"🔍 File exists: {os.path.exists(favicon_path)}")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/svg+xml")
    else:
        print(f"❌ Favicon file not found at {favicon_path}")
        raise FileNotFoundError(f"Favicon not found at {favicon_path}")

# Create uploads directory if not exists
os.makedirs("uploads/auth", exist_ok=True)
os.makedirs("uploads/lab_tests", exist_ok=True)
os.makedirs("uploads/about_us", exist_ok=True)
os.makedirs("uploads/medicine", exist_ok=True)
os.makedirs("uploads/pharma_shop", exist_ok=True)
os.makedirs("uploads/prescriptions", exist_ok=True)

# Mount static files for uploads
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Mount static files (including favicon)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register routers
app.include_router(patho_lab_router)
app.include_router(pharma_shop_router)
app.include_router(customer_router)
app.include_router(cart_router)
app.include_router(core_test_router)
app.include_router(lab_test_inventory_router)
app.include_router(test_package_router)
app.include_router(test_package_booking_router)
app.include_router(about_us_router)
app.include_router(medicine_router)
app.include_router(medicine_order_ws_router)
app.include_router(terms_conditions_router)
app.include_router(privacy_policy_router)

if __name__ == "__main__":
    # Running on 0.0.0.0 to make it accessible on all network interfaces
    uvicorn.run(app, host="0.0.0.0", port=8000)
