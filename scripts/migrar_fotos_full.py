#!/usr/bin/env python3
"""Migración one-shot: crea versión original (full/) para fotos existentes
y re-comprime la versión web a 1200px JPEG q80.

Uso:
    cd backend && ../venv/Scripts/python.exe ../scripts/migrar_fotos_full.py
  o
    cd backend && python ../scripts/migrar_fotos_full.py
"""
import os, sys

# Asegurar que app/ sea importable
backend_dir = os.path.dirname(os.path.abspath(__file__))
# subir de scripts/ a la raíz del proyecto
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, os.path.join(project_root, "backend"))

from PIL import Image
from app.routers.mobiliario import UPLOAD_DIR, FULL_DIR, MAX_FOTO_SIZE, JPEG_QUALITY
from app.database import SessionLocal
from app.models import Mobiliario

os.makedirs(FULL_DIR, exist_ok=True)

db = SessionLocal()
items = db.query(Mobiliario).filter(
    Mobiliario.foto_path != None, Mobiliario.foto_path != ""
).all()
print(f"Mobiliarios con foto: {len(items)}")

procesadas = 0
saltadas = 0
for m in items:
    web_path = os.path.join(UPLOAD_DIR, m.foto_path)
    full_path = os.path.join(FULL_DIR, m.foto_path)

    if os.path.exists(full_path):
        saltadas += 1
        continue

    if not os.path.exists(web_path):
        print(f"  SKIP {m.nombre}: web no existe")
        continue

    # 1) Copiar la actual como original a full/
    with open(web_path, "rb") as src, open(full_path, "wb") as dst:
        dst.write(src.read())

    # 2) Re-comprimir la web a 1200px JPEG q80
    img = Image.open(web_path)
    img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > MAX_FOTO_SIZE:
        if w >= h:
            new_w, new_h = MAX_FOTO_SIZE, int(h * (MAX_FOTO_SIZE / w))
        else:
            new_h, new_w = MAX_FOTO_SIZE, int(w * (MAX_FOTO_SIZE / h))
        img = img.resize((new_w, new_h), Image.LANCZOS)
    img.save(web_path, "JPEG", quality=JPEG_QUALITY, optimize=True)

    old_kb = os.path.getsize(full_path) // 1024
    new_kb = os.path.getsize(web_path) // 1024
    print(f"  {m.nombre}: {old_kb}KB -> {new_kb}KB")
    procesadas += 1

db.close()
print(f"\nListo: {procesadas} procesadas, {saltadas} ya tenian full/")
