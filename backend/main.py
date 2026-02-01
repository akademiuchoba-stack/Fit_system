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
    # Логика: если разница меньше 4см - туго
    if p.garment_chest:
        diff = p.garment_chest - u.get('chest', 0)
        if diff < 4: res['грудь'] = "Туго"; score -= 2
        elif diff > 15: res['грудь'] = "Оверсайз"; score -= 1
        else: res['грудь'] = "Идеально"
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
            "id": p.id, "name": p.name, "sku": p.sku, "score": m['score'], "details": m['details'],
            "parsed": {"chest": p.garment_chest, "waist": p.garment_waist, "img": p.image_url}
        })
    return sorted(out, key=lambda x: x['score'], reverse=True)

@app.post("/api/save-test")
async def save_test(data: dict = Body(...), db: Session = Depends(get_db)):
    test = MeasurementTest(
        user_name=data['user_name'], product_id=data['product_id'],
        u_chest=data['u_chest'], u_waist=data['u_waist'], u_hips=data['u_hips'], u_height=data['u_height'],
        real_chest=data['real_chest'], real_waist=data['real_waist'],
        fit_ok=data['fit_ok'], conclusion=data['conclusion']
    )
    db.add(test); db.commit(); return {"status": "ok"}

@app.get("/api/admin/stats")
async def get_stats(db: Session = Depends(get_db)):
    tests = db.query(MeasurementTest).all()
    return [{
        "date": t.timestamp.strftime("%d.%m %H:%M"), "user": t.user_name,
        "product": (db.query(Product).filter(Product.id==t.product_id).first()).name,
        "real": f"Г:{t.real_chest} Т:{t.real_waist}", "ok": "✓" if t.fit_ok else "✗", "note": t.conclusion
    } for t in tests]

app.mount("/static", StaticFiles(directory="../frontend"), name="static")
@app.get("/")
async def index(): return FileResponse("../frontend/index.html")