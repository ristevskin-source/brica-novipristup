import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import baza

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

baza.init_db()

class RezervacijaReq(BaseModel):
    datum: str
    vreme: str
    ime: str
    telefon: str
    usluga: str
    cena: int

class UslugaReq(BaseModel):
    ime: str
    cena: int
    trajanje: int

class OtkaziReq(BaseModel):
    datum: str
    vreme: str

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html")

@app.get("/api/usluge")
async def get_usluge():
    conn = baza.get_connection()
    c = conn.cursor()
    c.execute("SELECT id, ime, cena, trajanje FROM usluge")
    redovi = c.fetchall()
    conn.close()
    return [{"id": r[0], "ime": r[1], "cena": r[2], "trajanje": r[3]} for r in redovi]

@app.post("/api/usluge")
async def add_usluga(u: UslugaReq):
    conn = baza.get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO usluge (ime, cena, trajanje) VALUES (?, ?, ?)", (u.ime, u.cena, u.trajanje))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.delete("/api/usluge/{usluga_id}")
async def delete_usluga(usluga_id: int):
    conn = baza.get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM usluge WHERE id=?", (usluga_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/api/slotovi/{datum}")
async def get_slotovi(datum: str):
    return baza.get_slotovi_za_datum(datum)

@app.post("/api/zakazi")
async def zakazi(req: RezervacijaReq):
    uspeh = baza.zakazi_termin(req.datum, req.vreme, req.ime, req.telefon, req.usluga, req.cena)
    if uspeh:
        return {"status": "ok", "poruka": "Termin uspešno zakazan!"}
    return {"status": "error", "poruka": "Termin je već zauzet!"}

@app.post("/api/otkazi")
async def otkazi(req: OtkaziReq):
    conn = baza.get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE rezervacije 
        SET ime=NULL, telefon=NULL, usluga=NULL, cena=NULL, status='slobodan' 
        WHERE datum=? AND vreme=?
    """, (req.datum, req.vreme))
    conn.commit()
    conn.close()
    return {"status": "ok"}
