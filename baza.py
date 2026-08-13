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
    c.execute("SELECT vreme, status FROM rezervacije WHERE datum = ?", (datum,))
    zauzeti = {row['vreme']: row['status'] for row in c.fetchall()}
    conn.close()

    # Generišemo standardne radne termine od 09:00 do 17:00 na 30 min
    svi_slotovi = []
    start = datetime.strptime("09:00", "%H:%M")
    end = datetime.strptime("19:30", "%H:%M")
    
    while start < end:
        vreme_str = start.strftime("%H:%M")
        status = zauzeti.get(vreme_str, 'slobodan')
        svi_slotovi.append({
            'vreme': vreme_str,
            'status': status
        })
        start += timedelta(minutes=30)

    return jsonify(svi_slotovi)

@app.route('/api/usluge/<int:id>', methods=['PUT', 'DELETE'])
def api_usluge_id(id):
    conn = get_connection()
    c = conn.cursor()
    if request.method == 'PUT':
        data = request.get_json()
        nova_cena = data.get('cena')
        c.execute("UPDATE usluge SET cena = ? WHERE id = ?", (nova_cena, id))
        conn.commit()
        conn.close()
        return jsonify({'status': 'ok'})
    elif request.method == 'DELETE':
        c.execute("DELETE FROM usluge WHERE id = ?", (id,))
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
