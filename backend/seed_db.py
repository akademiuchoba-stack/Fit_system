import os
import sys
from pathlib import Path

# root -> чтобы работали imports "backend.*"
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from backend import models, database


def seed_data():
    print("🚀 Fit_system: Start Database Initialization (v3.1 seed)")

    # ensure folders
    os.makedirs(database.SHOPS_DIR, exist_ok=True)

    print("🏗 Building schema...")
    models.Base.metadata.create_all(bind=database.engine)

    db = database.SessionLocal()
    try:
        if db.query(models.Garment).count() > 0:
            print("⚠️ Database already contains data. Skipping seed to prevent duplicates.")
            return

        print("🧪 Seeding 2 demo garments in v3.1...")

        tshirt_v31 = {
            "engine": {"version": "fit_v3.1"},
            "product": {
                "sku": "DEMO-TS-001",
                "garment_type": "tshirt",
                "fit_profile": "regular",
                "available_sizes": ["M", "L", "XL"],
            },
            "fabric": {"fabric_type": "knit", "elastane_pct": 3, "stiffness": "medium"},
            "model": {
                "gender": "male",
                "size_worn": "L",
                "body": {
                    "chest_circ": 100,
                    "waist_top_circ": 86,
                    "belly_circ": 94,
                    "hips_circ": 100,
                    "bicep_circ": 34,
                },
            },
            "garment_on_model": {
                "size": "L",
                "measurement_convention": "flat_half",
                "measurements": {
                    "chest": 58,         # half
                    "waist_top": 56,     # half
                    "hem_top": 56,       # half
                    "sleeve": 22,        # length
                    "length_top": 73     # length
                },
            },
            "size_matrix": {
                "M": {"measured": True, "measurements": {"chest": 56, "waist_top": 54, "hem_top": 54, "sleeve": 21, "length_top": 71}},
                "L": {"measured": True, "measurements": {"chest": 58, "waist_top": 56, "hem_top": 56, "sleeve": 22, "length_top": 73}},
                "XL": {"measured": True, "measurements": {"chest": 61, "waist_top": 59, "hem_top": 59, "sleeve": 23, "length_top": 75}},
            },
        }

        trousers_v31 = {
            "engine": {"version": "fit_v3.1"},
            "product": {
                "sku": "DEMO-TR-001",
                "garment_type": "trousers",
                "fit_profile": "regular",
                "available_sizes": ["M", "L", "XL"],
            },
            "fabric": {"fabric_type": "woven", "elastane_pct": 2, "stiffness": "medium"},
            "model": {
                "gender": "male",
                "size_worn": "L",
                "body": {
                    "waist_top_circ": 86,
                    "belly_circ": 94,
                    "hips_circ": 100,
                    "inseam_len": 80,
                },
            },
            "garment_on_model": {
                "size": "L",
                "measurement_convention": "flat_half",
                "measurements": {
                    "waist_bottom": 44,   # half
                    "hips": 54,           # half
                    "inseam": 80,         # length
                },
            },
            "size_matrix": {
                "M": {"measured": True, "measurements": {"waist_bottom": 42, "hips": 52, "inseam": 79}},
                "L": {"measured": True, "measurements": {"waist_bottom": 44, "hips": 54, "inseam": 80}},
                "XL": {"measured": True, "measurements": {"waist_bottom": 46, "hips": 56, "inseam": 81}},
            },
        }

        items = [
            {
                "sku": "DEMO-TS-001",
                "name": "Demo T-shirt Regular",
                "platform": "demo",
                "price": 1990.0,
                "image_url": "https://images.unsplash.com/photo-1520975958225-7f61d1f94b7a?auto=format&fit=crop&q=80&w=800",
                "in_stock": True,
                "metrics": {"schema_version": "v3.1", "v31": tshirt_v31},
            },
            {
                "sku": "DEMO-TR-001",
                "name": "Demo Trousers Regular",
                "platform": "demo",
                "price": 3490.0,
                "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&q=80&w=800",
                "in_stock": True,
                "metrics": {"schema_version": "v3.1", "v31": trousers_v31},
            },
        ]

        for d in items:
            db.add(models.Garment(**d))

        db.commit()
        print("✅ Seed complete (v3.1).")

    except Exception as e:
        db.rollback()
        print(f"❌ Error during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
