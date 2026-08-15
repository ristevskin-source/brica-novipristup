import sqlite3 
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
DB_NAME = 'brica.db'

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
            status TEXT DEFAULT 'zakazan'
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
    
    # Dnevna zarada
    c.execute("SELECT COALESCE(SUM(cena), 0) FROM naplate WHERE datum = DATE('now')")
    danas = c.fetchone()[0]
    
    # Mesečna zarada
    c.execute("SELECT COALESCE(SUM(cena), 0) FROM naplate WHERE strftime('%Y-%m', datum) = strftime('%Y-%m', 'now')")
    mesec = c.fetchone()[0]

    # Godišnja zarada
    c.execute("SELECT COALESCE(SUM(cena), 0) FROM naplate WHERE strftime('%Y', datum) = strftime('%Y', 'now')")
    godina = c.fetchone()[0]
    
    conn.close()
    return {"danas": danas, "mesec": mesec, "godina": godina}

init_db()

def get_raspored_za_period(pocetak_str, kraj_str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT r.datum, r.vreme, r.ime, r.usluga, r.cena, COALESCE(u.trajanje, 30) as trajanje
        FROM rezervacije r
        LEFT JOIN usluge u ON r.usluga = u.ime
        WHERE r.datum >= ? AND r.datum <= ? AND r.status = 'zakazan'
    """, (pocetak_str, kraj_str))
    
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
    return render_template('admin.html', v='1.1')

# --- API RUTE ---
@app.route('/api/slotovi/<datum>', methods=['GET'])
def api_slotovi(datum):
    # Ako je nedelja (weekday() == 6), vrati praznu listu - nema slobodnih termina
    dt = datetime.strptime(datum, "%Y-%m-%d")
    if dt.weekday() == 6:
        return jsonify([])
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT r.vreme, COALESCE(u.trajanje, 30) as trajanje
        FROM rezervacije r
        LEFT JOIN usluge u ON r.usluga = u.ime
        WHERE r.datum = ? AND r.status = 'zakazan'
    """, (datum,))
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
    start = datetime.strptime("09:00", "%H:%M")
    end = datetime.strptime("20:00", "%H:%M")

    while start < end:
        vreme_str = start.strftime("%H:%M")
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
        return jsonify({'status': 'ok'})

@app.route('/api/zakazi', methods=['POST'])
def api_zakazi():
    data = request.get_json()
    datum = data.get('datum')
    vreme = data.get('vreme')
    
    # 1. Provera: Nedeljom ne radimo (6 = nedelja)
    dt_zakazi = datetime.strptime(datum, "%Y-%m-%d")
    if dt_zakazi.weekday() == 6:
        return jsonify({'status': 'error', 'poruka': 'Nedeljom ne radimo!'}), 400

    # 2. Provera: Sprečavanje zakazivanja u prošlosti (SRB vreme UTC+2)
    srbija_vreme = datetime.utcnow() + timedelta(hours=2)
    danas_str = srbija_vreme.strftime('%Y-%m-%d')
    if datum < danas_str:
        return jsonify({'status': 'error', 'poruka': 'Nije moguće zakazati u prošlosti!'}), 400
        
    if datum == danas_str:
        trenutno_vreme = srbija_vreme.strftime('%H:%M')
        if vreme < trenutno_vreme:
            return jsonify({'status': 'error', 'poruka': 'Izabrani termin je već prošao!'}), 400

    ime = data.get('ime')
    telefon = data.get('telefon')
    usluga = data.get('usluga')
    cena = data.get('cena')
    
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO rezervacije (datum, vreme, ime, telefon, usluga, cena, status)
        VALUES (?, ?, ?, ?, ?, ?, 'zakazan')
    """, (datum, vreme, ime, telefon, usluga, cena))
    conn.commit()
    conn.close()
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
    
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM rezervacije WHERE datum = ? AND vreme = ?", (datum, vreme))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/statistika', methods=['GET'])
def api_statistika():
    statistika = uzmi_statistiku_zarade()
    return jsonify(statistika)

if __name__ == '__main__':
    app.run(debug=True, port=5000)

@app.route('/api/nedelja', methods=['GET'])
def api_nedelja():
    pocetak = request.args.get('pocetak')
    kraj = request.args.get('kraj')
    
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT datum, vreme, ime, usluga, cena, telefon, status, trajanje FROM rezervacije WHERE datum BETWEEN ? AND ?", (pocetak, kraj))
    rezervacije = c.fetchall()
    conn.close()
    
    raspored = {}
    for r in rezervacije:
        datum, vreme, ime, usluga, cena, telefon, status, trajanje = r
        if datum not in raspored:
            raspored[datum] = {}
        raspored[datum][vreme] = {
            'ime': ime,
            'usluga': usluga,
            'cena': cena,
            'telefon': telefon,
            'status': status,
            'trajanje': trajanje or 30
        }
        
    return jsonify(raspored)
