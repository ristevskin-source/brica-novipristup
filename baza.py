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
    conn.commit()
    conn.close()

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
    return render_template('admin.html')

# --- API RUTE ---
@app.route('/api/slotovi/<datum>', methods=['GET'])
def api_slotovi(datum):
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

@app.route('/api/raspored_nedelja', methods=['GET'])
def api_raspored_nedelja():
    pocetak = request.args.get('pocetak')
    kraj = request.args.get('kraj')
    if not pocetak or not kraj:
        return jsonify({'poruka': 'Nedostaju parametri'}), 400
    return jsonify(get_raspored_za_period(pocetak, kraj))

@app.route('/api/zakazi', methods=['POST'])
def api_zakazi():
    data = request.get_json()
    datum = data.get('datum')
    vreme = data.get('vreme')
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

@app.route('/api/otkazi', methods=['POST'])
def api_otkazi():
    data = request.get_json()
    datum = data.get('datum')
    vreme = data.get('vreme')

    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM rezervacije WHERE datum = ? AND vreme = ?", (datum, vreme))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
