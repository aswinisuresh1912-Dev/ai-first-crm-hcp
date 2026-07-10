from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.config import settings
from backend.models import Base, HCP, Material, Sample

# Check if using SQLite to apply extra config for thread safety
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    seed_data()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_data():
    db = SessionLocal()
    try:
        # Check if HCP table is empty
        if db.query(HCP).count() == 0:
            hcps = [
                HCP(name="Dr. Smith", specialty="Oncology", email="dr.smith@oncology-assoc.com"),
                HCP(name="Dr. John", specialty="Cardiology", email="john.cardio@healthnet.com"),
                HCP(name="Dr. Sharma", specialty="Neurology", email="sharma.n@cityhospital.org"),
                HCP(name="Dr. Elizabeth", specialty="Pediatrics", email="drelizabeth@kidsfirst.org"),
                HCP(name="Dr. Davis", specialty="Internal Medicine", email="davis.im@metromed.com")
            ]
            db.bulk_save_objects(hcps)
            db.commit()
            print("Database seeded with HCPs.")

        # Check if Material table is empty
        if db.query(Material).count() == 0:
            materials = [
                Material(name="OncoBoost Phase III PDF", description="Clinical trial results for OncoBoost Phase III study."),
                Material(name="Product X Brochure", description="Informative brochure detailing Product X benefits and dosage."),
                Material(name="CardioShield Clinical Study", description="Efficacy and safety trial report for CardioShield."),
                Material(name="NeuroVibe Product Manual", description="Detailed prescribing information and product specs for NeuroVibe.")
            ]
            db.bulk_save_objects(materials)
            db.commit()
            print("Database seeded with materials.")

        # Check if Sample table is empty
        if db.query(Sample).count() == 0:
            samples = [
                Sample(name="Product X Sample Pack", description="Starter dose pack of Product X (5 x 10mg)."),
                Sample(name="CardioShield Starter Kit", description="Introductory starter kit containing CardioShield (10 days supply)."),
                Sample(name="NeuroVibe Dosage Guide", description="Visual titration guide and patient starter pack for NeuroVibe.")
            ]
            db.bulk_save_objects(samples)
            db.commit()
            print("Database seeded with samples.")

    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()
