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
        c.execute("INSERT INTO usluge (ime, cena, trajanje) VALUES ('Šišanje + Brada', 1500, 45)")

    c.execute('''
        CREATE TABLE IF NOT EXISTS rezervacije (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datum TEXT NOT NULL,
            vreme TEXT NOT NULL,
            ime TEXT,
            telefon TEXT,
            usluga TEXT,
            cena INTEGER,
            status TEXT DEFAULT 'slobodan'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_slotovi_za_datum(datum_str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM rezervacije WHERE datum = ?", (datum_str,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_raspored_za_period(pocetak_str, kraj_str):
    pocetak_dt = datetime.strptime(pocetak_str, "%Y-%m-%d")
    kraj_dt = datetime.strptime(kraj_str, "%Y-%m-%d")
    
    rezultat = {}
    trenutni = pocetak_dt
    while trenutni <= kraj_dt:
        d_str = trenutni.strftime("%Y-%m-%d")
        slotovi = get_slotovi_za_datum(d_str)
        rezultat[d_str] = {}
        for s in slotovi:
            if s.get('status') == 'zakazan':
                rezultat[d_str][s['vreme']] = {
                    "status": "zauzet",
                    "ime": s.get('ime', ''),
                    "usluga": s.get('usluga', ''),
                    "cena": s.get('cena', 0)
                }
        trenutni += timedelta(days=1)
    return rezultat

# --- FLASK RUTE ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/api/slotovi/<datum>', methods=['GET'])
def api_slotovi(datum):
    conn = get_connection()
    c = conn.cursor()
    
    # Uzimamo zakazane termne i trajanje usluge za svaki termin
    c.execute("""
        SELECT r.vreme, COALESCE(u.trajanje, 30) as trajanje 
        FROM rezervacije r 
        LEFT JOIN usluge u ON r.usluga = u.ime 
        WHERE r.datum = ? AND r.status = 'zakazan'
    """, (datum,))
    
    rezervacije = c.fetchall()
    conn.close()

    # Pravimo skup svih blokova koji su zauzeti (uključujući i blokove koje zahvata trajanje)
    zauzeti_slotovi = set()
    for r in rezervacije:
        pocetak = datetime.strptime(r['vreme'], "%H:%M")
        trajanje = int(r['trajanje'])
        
        # Prolazimo kroz sve blokove od po 30 minuta unutar trajanja usluge
        trenutni = pocetak
        kraj = pocetak + timedelta(minutes=trajanje)
        while trenutni < kraj:
            zauzeti_slotovi.add(trenutni.strftime("%H:%M"))
            trenutni += timedelta(minutes=30)

    # Generišemo termine od 09:00 do 20:00
    svi_slotovi = []
    start = datetime.strptime("09:00", "%H:%M")
    end = datetime.strptime("20:00", "%H:%M")
    
    while start < end:
        vreme_str = start.strftime("%H:%M")
        status = 'zauzet' if vreme_str in zauzeti_slotovi else 'slobodan'
        svi_slotovi.append({
            'vreme': vreme_str,
            'status': status
        })
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
        c.execute("INSERT INTO usluge (ime, cena, trajanje) VALUES (?, ?, 30)", (ime, cena))
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
