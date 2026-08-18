import sqlite3 
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
import os

app = Flask(__name__)
DB_NAME = os.environ.get('DB_NAME', 'brica.db')

# Simple favicon route to avoid 404 in browser console
@app.route('/favicon.ico')
def favicon():
return ('', 204)

def get_connection():
conn = sqlite3.connect(DB_NAME)
conn.row_factory = sqlite3.Row
return conn

def init_db():
conn = get_connection()
c = conn.cursor()
c.execute('''
       CREATE TABLE IF NOT EXISTS usluge (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           ime TEXT NOT NULL,
           cena INTEGER NOT NULL,
           trajanje INTEGER NOT NULL
       )
   ''')
c.execute("SELECT COUNT(*) FROM usluge")
if c.fetchone()[0] == 0:
c.execute("INSERT INTO usluge (ime, cena, trajanje) VALUES ('Šišanje', 1000, 30)")
c.execute("INSERT INTO usluge (ime, cena, trajanje) VALUES ('Brada / Brijanje', 600, 30)")
c.execute("INSERT INTO usluge (ime, cena, trajanje) VALUES ('Šišanje + Brada', 1500, 60)")

c.execute('''
       CREATE TABLE IF NOT EXISTS rezervacije (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           datum TEXT NOT NULL,
           vreme TEXT NOT NULL,
           ime TEXT,
           telefon TEXT,
           usluga TEXT,
           cena INTEGER,
           status TEXT DEFAULT 'zakazan',
           kreirano TIMESTAMP DEFAULT CURRENT_TIMESTAMP
       )
   ''')

c.execute('''
       CREATE TABLE IF NOT EXISTS naplate (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           datum TEXT NOT NULL,
           vreme TEXT NOT NULL,
           klijent TEXT,
           usluga TEXT,
           cena INTEGER NOT NULL,
           kreirano TIMESTAMP DEFAULT CURRENT_TIMESTAMP
       )
   ''')
conn.commit()
conn.close()

def zabelezi_naplatu(datum, vreme, klijent, usluga, cena):
conn = get_connection()
c = conn.cursor()
c.execute('''
       INSERT INTO naplate (datum, vreme, klijent, usluga, cena)
       VALUES (?, ?, ?, ?, ?)
   ''', (datum, vreme, klijent, usluga, cena))
conn.commit()
conn.close()

def uzmi_statistiku_zarade():
conn = get_connection()
c = conn.cursor()

c.execute("SELECT COALESCE(SUM(cena), 0) FROM naplate WHERE datum = DATE('now')")
danas = c.fetchone()[0]

c.execute("SELECT COALESCE(SUM(cena), 0) FROM naplate WHERE strftime('%Y-%m', datum) = strftime('%Y-%m', 'now')")
mesec = c.fetchone()[0]

c.execute("SELECT COALESCE(SUM(cena), 0) FROM naplate WHERE strftime('%Y', datum) = strftime('%Y', 'now')")
godina = c.fetchone()[0]

conn.close()
return {"danas": danas, "mesec": mesec, "godina": godina}

init_db()

def get_raspored_za_period(pocetak_str, kraj_str):
conn = get_connection()
c = conn.cursor()
c.execute('''
       SELECT r.datum, r.vreme, r.ime, r.usluga, r.cena, COALESCE(u.trajanje, 30) as trajanje
       FROM rezervacije r
       LEFT JOIN usluge u ON r.usluga = u.ime
       WHERE r.datum >= ? AND r.datum <= ? AND r.status = 'zakazan'
   ''', (pocetak_str, kraj_str))

rows = c.fetchall()
conn.close()

rezultat = {}
for r in rows:
datum = r["datum"]
vreme = r["vreme"]
if datum not in rezultat:
rezultat[datum] = {}
rezultat[datum][vreme] = {
"status": "zauzet",
"ime": r["ime"],
"usluga": r["usluga"],
"cena": r["cena"],
"trajanje": r["trajanje"]
}
return rezultat

# --- FLASK RUTE ZA PRIKAZ STRANICA ---
@app.route('/')
def index():
return render_template('index.html')

@app.route('/admin')
def admin():
return render_template('admin.html', v='1.3')

# --- API RUTE ---
@app.route('/api/slotovi/<datum>', methods=['GET'])
def api_slotovi(datum):
try:
dt = datetime.strptime(datum, "%Y-%m-%d")
except:
return jsonify([]), 400

# Nedelja = 6, a mi radimo Pon-Ned (0-5)
if dt.weekday() == 6:
return jsonify([])

# Provera da li je datum u prošlosti
srbija_vreme = datetime.utcnow() + timedelta(hours=2)
danas_str = srbija_vreme.strftime('%Y-%m-%d')

if datum < danas_str:
return jsonify([])

conn = get_connection()
c = conn.cursor()
c.execute('''
       SELECT r.vreme, COALESCE(u.trajanje, 30) as trajanje
       FROM rezervacije r
       LEFT JOIN usluge u ON r.usluga = u.ime
       WHERE r.datum = ? AND r.status = 'zakazan'
   ''', (datum,))
rezervacije = c.fetchall()
conn.close()

zauzeti_slotovi = set()
for r in rezervacije:
pocetak = datetime.strptime(r['vreme'], "%H:%M")
trajanje = int(r['trajanje'])
trenutni = pocetak
kraj = pocetak + timedelta(minutes=trajanje)
while trenutni < kraj:
zauzeti_slotovi.add(trenutni.strftime("%H:%M"))
trenutni += timedelta(minutes=30)

svi_slotovi = []
start = datetime.strptime(f"{datum} 09:00", "%Y-%m-%d %H:%M")
start = start.replace(tzinfo=None)  # <-- DODAJ OVO
end = datetime.strptime(f"{datum} 20:00", "%Y-%m-%d %H:%M")
end = end.replace(tzinfo=None)  # <-- DODAJ OVO

# Ako je danas, počni od sledećeg slobodnog slota (30 min od sada)
if datum == danas_str:
    trenutno_vreme = srbija_vreme
    # Zaokruži na sledeću 30-minutsku granicu
    if trenutno_vreme.minute > 0:
        trenutno_vreme = trenutno_vreme.replace(minute=0) + timedelta(hours=1)
    else:
        trenutno_vreme = trenutno_vreme + timedelta(minutes=30)

    start = trenutno_vreme
    end = datetime.strptime(f"{datum} 20:00", "%Y-%m-%d %H:%M")
    
    # 🔧 DODAJ OVU LINIJU - UKLANJA VREMENSKU ZONU SA START-A
    start = start.replace(tzinfo=None)

    while start < end:
        vreme_str = start.strftime("%H:%M")
        # Pauza: 13:00-14:00
        if vreme_str >= "13:00" and vreme_str < "14:00":
            start += timedelta(minutes=30)
            continue
        status = 'zauzet' if vreme_str in zauzeti_slotovi else 'slobodan'
        svi_slotovi.append({'vreme': vreme_str, 'status': status})
        start += timedelta(minutes=30)

    return jsonify(svi_slotovi)

@app.route('/api/usluge', methods=['GET', 'POST'])
def api_usluge():
conn = get_connection()
c = conn.cursor()
if request.method == 'GET':
c.execute("SELECT * FROM usluge")
usluge = [dict(row) for row in c.fetchall()]
conn.close()
return jsonify(usluge)
elif request.method == 'POST':
data = request.get_json()
ime = data.get('ime')
cena = data.get('cena')
trajanje = data.get('trajanje', 30)
c.execute("INSERT INTO usluge (ime, cena, trajanje) VALUES (?, ?, ?)", (ime, cena, trajanje))
conn.commit()
conn.close()
return jsonify({'status': 'ok', 'id': c.lastrowid})

@app.route('/api/usluge/<int:id>', methods=['PUT', 'DELETE'])
def api_usluga_id(id):
conn = get_connection()
c = conn.cursor()

if request.method == 'PUT':
data = request.get_json()
ime = data.get('ime')
cena = data.get('cena')
trajanje = data.get('trajanje', 30)
c.execute("UPDATE usluge SET ime=?, cena=?, trajanje=? WHERE id=?", (ime, cena, trajanje, id))
conn.commit()
conn.close()
return jsonify({'status': 'ok'})

elif request.method == 'DELETE':
c.execute("DELETE FROM usluge WHERE id=?", (id,))
conn.commit()
conn.close()
return jsonify({'status': 'ok'})

@app.route('/api/zakazi', methods=['POST'])
def api_zakazi():
data = request.get_json() or {}
datum = data.get('datum')
vreme = data.get('vreme')

# basic validations
try:
dt_zakazi = datetime.strptime(datum, "%Y-%m-%d")
except Exception:
return jsonify({'status': 'error', 'poruka': 'Neispravan datum'}), 400

if dt_zakazi.weekday() == 6:
return jsonify({'status': 'error', 'poruka': 'Nedeljom ne radimo!'}), 400

# Vremenska validacija — STROŽIJA!
srbija_vreme = datetime.utcnow() + timedelta(hours=2)
danas_str = srbija_vreme.strftime('%Y-%m-%d')

if datum < danas_str:
return jsonify({'status': 'error', 'poruka': 'Nije moguće zakazati u prošlosti!'}), 400

if datum == danas_str:
trenutno_vreme = srbija_vreme.strftime('%H:%M')
# Dodaj 30 minuta minimalnog vremena čekanja
min_vreme = (srbija_vreme + timedelta(minutes=30)).strftime('%H:%M')
if vreme < min_vreme:
return jsonify({'status': 'error', 'poruka': 'Termin mora biti najmanje 30 minuta od sada!'}), 400

ime = (data.get('ime') or '').strip()
telefon = (data.get('telefon') or '').strip()
usluga_ime = data.get('usluga')
cena_input = data.get('cena')

if not ime or not telefon:
return jsonify({'status': 'error', 'poruka': 'Ime i telefon su obavezni'}), 400

conn = get_connection()
c = conn.cursor()

# find service duration and price from usluge table
trajanje = int(data.get('trajanje', 30))
cena = int(cena_input) if cena_input is not None else 0
if usluga_ime:
c.execute("SELECT trajanje, cena FROM usluge WHERE ime = ?", (usluga_ime,))
svc = c.fetchone()
if svc:
trajanje = int(svc['trajanje'])
cena = int(svc['cena']) if svc['cena'] is not None else cena

# compute required 30-min slots
sloti = []
try:
t = datetime.strptime(vreme, "%H:%M")
except Exception:
conn.close()
return jsonify({'status':'error','poruka':'Neispravno vreme'}), 400

broj = (trajanje + 29) // 30  # ceil to 30-min slots
for i in range(broj):
sloti.append(t.strftime("%H:%M"))
t += timedelta(minutes=30)

# check against working hours (last slot should not exceed 20:00)
if sloti:
poslednje = datetime.strptime(sloti[-1], "%H:%M")
if poslednje >= datetime.strptime("20:00", "%H:%M"):
conn.close()
return jsonify({'status':'error','poruka':'Usluga prevazilazi radno vreme'}), 400

# check pause (13:00-14:00)
for s in sloti:
if "13:00" <= s < "14:00":
conn.close()
return jsonify({'status':'error','poruka':'Izabrano vreme pada u pauzu'}), 400

# check availability — STROGA PROVERA SVIH SLOTOVA!
conflicts = []
for s in sloti:
c.execute("SELECT id, ime FROM rezervacije WHERE datum=? AND vreme=? AND status='zakazan'", (datum, s))
row = c.fetchone()
if row and row['ime']:
conflicts.append(s)

if conflicts:
conn.close()
return jsonify({'status':'error', 'poruka':'Nema dovoljno slobodnih termina', 'conflicts': conflicts}), 400

# reserve slots: first slot gets price, others 0
try:
prvi = True
for s in sloti:
cena_slot = cena if prvi else 0
c.execute("SELECT id FROM rezervacije WHERE datum=? AND vreme=?", (datum, s))
row = c.fetchone()
if row:
# update existing placeholder row
c.execute("UPDATE rezervacije SET ime=?, telefon=?, usluga=?, cena=?, status='zakazan' WHERE id=?",
(ime, telefon, usluga_ime, cena_slot, row['id']))
else:
c.execute("INSERT INTO rezervacije (datum, vreme, ime, telefon, usluga, cena, status) VALUES (?,?,?,?,?,?,?)",
(datum, s, ime, telefon, usluga_ime, cena_slot, 'zakazan'))
prvi = False
conn.commit()
# Vrati potvrdu sa svim detaljima
return jsonify({
'status': 'ok',
'poruka': 'Termin uspešno zakazan!',
'rezervacija': {
'datum': datum,
'vreme': vreme,
'ime': ime,
'telefon': telefon,
'usluga': usluga_ime,
'cena': cena
}
})
except Exception as e:
conn.rollback()
return jsonify({'status':'error','poruka':str(e)}), 500
finally:
conn.close()

@app.route('/api/otkazi', methods=['POST'])
def api_otkazi():
data = request.get_json()
datum = data.get('datum')
vreme = data.get('vreme')

conn = get_connection()
c = conn.cursor()

    # Pronađi rezervaciju na kliknutom slotu
    c.execute("""
        SELECT ime, telefon, usluga
        FROM rezervacije
        WHERE datum = ? AND vreme = ? AND status = 'zakazan'
    """, (datum, vreme))

    rezervacija = c.fetchone()

    if not rezervacija:
        conn.close()
        return jsonify({
            'status': 'error',
            'poruka': 'Rezervacija nije pronađena'
        }), 404

    ime = rezervacija['ime']
    telefon = rezervacija['telefon']
    usluga = rezervacija['usluga']

    # Obriši SVE slotove koji pripadaju istoj rezervaciji
    c.execute("""
        DELETE FROM rezervacije
        WHERE datum = ?
          AND ime = ?
          AND telefon = ?
          AND usluga = ?
          AND status = 'zakazan'
    """, (datum, ime, telefon, usluga))

    obrisano = c.rowcount

    # Brisanje SAMO prvog slota (gde je cena)
    c.execute("DELETE FROM rezervacije WHERE datum = ? AND vreme = ?", (datum, vreme))
conn.commit()
conn.close()

    return jsonify({
        'status': 'ok',
        'obrisano_slotova': obrisano
    })
    return jsonify({'status': 'ok'})

@app.route('/api/naplati', methods=['POST'])
def api_naplati():
data = request.json
datum = data.get('datum')
vreme = data.get('vreme')
ime = data.get('ime', '')
usluga = data.get('usluga', '')
cena = data.get('cena', 0)

zabelezi_naplatu(datum, vreme, ime, usluga, cena)

# Obriši sve slotove za ovu rezervaciju (svi sa istim imenom i datumom)
conn = get_connection()
c = conn.cursor()
c.execute("SELECT vreme FROM rezervacije WHERE datum = ? AND ime = ? ORDER BY vreme", (datum, ime))
svi_slotovi = c.fetchall()

for slot_row in svi_slotovi:
c.execute("DELETE FROM rezervacije WHERE datum = ? AND vreme = ?", (datum, slot_row['vreme']))

conn.commit()
conn.close()
return jsonify({"status": "ok"})

@app.route('/api/statistika', methods=['GET'])
def api_statistika():
statistika = uzmi_statistiku_zarade()
return jsonify(statistika)

@app.route('/api/finansije', methods=['GET'])
def api_finansije():
od_datuma = request.args.get('od')
do_datuma = request.args.get('do')

conn = get_connection()
c = conn.cursor()

if od_datuma and do_datuma:
c.execute("SELECT COALESCE(SUM(cena), 0) FROM naplate WHERE datum BETWEEN ? AND ?", (od_datuma, do_datuma))
else:
c.execute("SELECT COALESCE(SUM(cena), 0) FROM naplate")

ukupno = c.fetchone()[0]
conn.close()
return jsonify({"ukupno": ukupno})

@app.route('/api/rezervacije', methods=['GET'])
def api_rezervacije():
conn = get_connection()
c = conn.cursor()
c.execute("SELECT * FROM rezervacije WHERE status='zakazan' ORDER BY datum DESC, vreme DESC")
rezervacije = [dict(row) for row in c.fetchall()]
conn.close()
return jsonify(rezervacije)

@app.route('/api/nedelja', methods=['GET'])
def api_nedelja():
pocetak = request.args.get('pocetak')
kraj = request.args.get('kraj')

if not pocetak or not kraj:
try:
offset = int(request.args.get('offset', 0))
except ValueError:
offset = 0

danas = datetime.now()
ponedeljak = danas - timedelta(days=danas.weekday()) + timedelta(weeks=offset)
nedelja = ponedeljak + timedelta(days=6)

pocetak = ponedeljak.strftime('%Y-%m-%d')
kraj = nedelja.strftime('%Y-%m-%d')

conn = get_connection()
c = conn.cursor()
# ISPRAVLJENA SQL QUERY — sa BETWEEN
c.execute("""
       SELECT r.datum, r.vreme, r.ime, r.usluga, r.cena, r.telefon, r.status, COALESCE(u.trajanje, 30) as trajanje 
       FROM rezervacije r 
       LEFT JOIN usluge u ON r.usluga = u.ime 
       WHERE r.datum BETWEEN ? AND ? AND r.status = 'zakazan'
       ORDER BY r.datum, r.vreme
   """, (pocetak, kraj))

rezervacije = c.fetchall()
conn.close()

raspored = {}
for r in rezervacije:
# unpack includes trajanje
datum, vreme, ime, usluga, cena, telefon, status, trajanje = r
if datum not in raspored:
raspored[datum] = {}
raspored[datum][vreme] = {
'ime': ime,
'usluga': usluga,
'cena': cena,
'telefon': telefon,
'status': status,
'trajanje': trajanje
}

return jsonify(raspored)

@app.route('/health')
def health():
return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
app.run(debug=True, port=5000)
