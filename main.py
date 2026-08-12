from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
import baza

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Inicijalizacija baze pri pokretanju
baza.init_db()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

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
        data['telefon'], data['usluga'], data['cena'], data['trajanje']
    )
    if uspesno:
        return {"status": "ok", "poruka": "Termin uspešno zakazan!"}
    return JSONResponse(status_code=400, content={"status": "error", "poruka": "Termin je u međuvremenu zauzet."})
