import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

def create_database_if_not_exists():
    try:
        # Connect to default postgres database to create the new one
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Check if database exists
        cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_NAME}'")
        exists = cur.fetchone()
        
        if not exists:
            cur.execute(f"CREATE DATABASE {DB_NAME}")
            print(f"Database {DB_NAME} created successfully.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error creating database: {e}")

# Create database if it doesn't exist
create_database_if_not_exists()

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from models.auth.patho_lab_user_models import PathoLabUser
    from models.auth.pharma_shop_user_models import PharmaShopUser
    from models.lab_test.core_test_models import CoreLabTest
    from models.lab_test.lab_test_inventory_models import TestInventory
    from models.lab_test.test_package_models import TestPackage
    from models.about_us.about_us_models import AboutUs
    from models.medicine.core_medicine_models import CoreMedicine
    from models.medicine.medicine_inventory_models import MedicineInventory
    from models.terms_conditions.terms_conditions_models import TermsConditions
    from models.privacy_policy.privacy_policy_models import PrivacyPolicy
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")
