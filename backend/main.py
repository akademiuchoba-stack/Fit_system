from fastapi import FastAPI, Depends, Body, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os, subprocess, datetime
from database import SessionLocal, Product, MeasurementTest, engine, Base

Base.metadata.create_all(bind=engine)
app = FastAPI()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def calculate_match(u, p):
    res = {}
    score = 5
    # Логика для верха
    if p.category == "верх" and p.garment_chest:
        diff = p.garment_chest - u.get('chest', 0)
        if diff < 4: res['грудь'] = "Туго"; score -= 2
        elif diff > 15: res['грудь'] = "Оверсайз"; score -= 1
        else: res['грудь'] = "ОК"
    # Логика для низа (талия/бедра)
    if p.garment_waist:
        diff_w = p.garment_waist - u.get('waist', 0)
        if diff_w < 2: res['талия'] = "Туго"; score -= 2
    return {"details": res, "score": max(0, score)}

@app.get("/api/products")
async def list_products(db: Session = Depends(get_db)):
    return db.query(Product).all()

@app.post("/api/match")
async def match_products(params: dict = Body(...), db: Session = Depends(get_db)):
    products = db.query(Product).all()
    out = []
    for p in products:
        m = calculate_match(params, p)
        out.append({
            "id": p.id, "name": p.name, "sku": p.sku, "size": p.size,
            "category": p.category, "image": p.image_url,
            "score": m['score'], "details": m['details'],
            "parsed": {"chest": p.garment_chest, "waist": p.garment_waist, "hips": p.garment_hips}
        })
    return sorted(out, key=lambda x: x['score'], reverse=True)

@app.post("/api/save-test")
async def save_test(data: dict = Body(...), db: Session = Depends(get_db)):
    test = MeasurementTest(
        user_name=data['user_name'], product_id=data['product_id'],
        u_chest=data['u_chest'], u_waist=data['u_waist'], u_hips=data['u_hips'],
        real_chest=data.get('real_chest'), real_waist=data.get('real_waist'),
        real_hips=data.get('real_hips'), fit_ok=data['fit_ok'], conclusion=data['conclusion']
    )
    db.add(test); db.commit(); return {"status": "ok"}

@app.get("/api/admin/stats")
async def get_stats(db: Session = Depends(get_db)):
    tests = db.query(MeasurementTest).all()
    res = []
    for t in tests:
        p = db.query(Product).filter(Product.id==t.product_id).first()
        res.append({
            "date": t.timestamp.strftime("%d.%m %H:%M"), "user": t.user_name,
            "product": f"{p.name} ({p.size})", "ok": "✓" if t.fit_ok else "✗", "note": t.conclusion
        })
    return res

app.mount("/static", StaticFiles(directory="../frontend"), name="static")
@app.get("/")
async def index(): return FileResponse("../frontend/index.html")