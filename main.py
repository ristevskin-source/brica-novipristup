import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import baza

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

try:
    baza.init_db()
except Exception as e:
    print(f"Greska pri inicijalizaciji baze: {e}")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

# ADMIN RUTA DODOATNA
@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html")

@app.get("/api/usluge")
async def get_usluge():
    return baza.get_usluge()

@app.get("/api/slotovi/{datum_str}")
async def get_slotovi(datum_str: str):
    baza.generisi_slotove_za_dan(datum_str)
    return baza.get_slotovi_za_dan(datum_str)

@app.post("/api/zakazi")
async def zakazi(data: dict):
    uspesno = baza.rezervisi_slotove(
        data['datum'], data['vreme'], data['ime'], 
        data['telefon'], data['usluga'], data['cena'], data.get('trajanje', 30)
    )
    if uspesno:
        return {"status": "ok", "poruka": "Termin uspešno zakazan!"}
    return JSONResponse(status_code=400, content={"status": "error", "poruka": "Termin je zauzet."})
