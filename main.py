import os
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import baza

app = FastAPI()
security = HTTPBasic()

def proveri_admina(credentials: HTTPBasicCredentials = Depends(security)):
    ispravno_ime = secrets.compare_digest(credentials.username, "admin")
    ispravna_lozinka = secrets.compare_digest(credentials.password, "srbkub")
    if not (ispravno_ime and ispravna_lozinka):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Netačno korisničko ime ili lozinka",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username



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

class AzurirajUsluguReq(BaseModel):
    cena: int

class OtkaziReq(BaseModel):
    datum: str
    vreme: str

@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, user: str = Depends(proveri_admina)):
    return templates.TemplateResponse(request=request, name="admin.html")


@app.get("/api/usluge")
async def get_usluge():
    return baza.get_sve_usluge()

@app.post("/api/usluge")
async def add_usluga(u: UslugaReq):
    baza.dodaj_uslugu(u.ime, u.cena, u.trajanje)
    return {"status": "ok"}

@app.put("/api/usluge/{usluga_id}")
async def update_usluga(usluga_id: int, req: AzurirajUsluguReq):
    baza.azuriraj_uslugu(usluga_id, req.cena)
    return {"status": "ok"}

@app.delete("/api/usluge/{usluga_id}")
async def delete_usluga(usluga_id: int):
    baza.obrisi_uslugu(usluga_id)
    return {"status": "ok"}

@app.get("/api/slotovi/{datum}")
async def get_slotovi(datum: str):
    return baza.get_slotovi_za_datum(datum)

@app.post("/api/zakazi")
async def zakazi(req: RezervacijaReq):
    # Uzimamo tačno trajanje usluge u minutima iz baze
    trajanje = baza.get_trajanje_usluge(req.usluga)
    
    # Pozivamo funkciju koja proverava i zauzima sve potrebne slotove odjednom
    uspeh = baza.zakazi_termin(
        req.datum, req.vreme, req.ime, req.telefon, req.usluga, req.cena, trajanje
    )
    
    if uspeh:
        return {"status": "ok", "poruka": "Termin uspešno zakazan!"}
    return {"status": "error", "poruka": "Termin ili neki od narednih slotova potrebnih za ovu uslugu je već zauzet!"}

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
@app.get("/api/raspored_nedelja")
async def get_raspored_nedelja(pocetak: str, kraj: str):
    return baza.get_raspored_za_period(pocetak, kraj)
