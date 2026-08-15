import sqlite3
from flask import Flask, request, jsonify
from datetime import datetime, timedelta

app = Flask(__name__)
DB_NAME = "brica.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Tabela usluga
    c.execute("""
        CREATE TABLE IF NOT EXISTS usluge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ime TEXT NOT NULL,
            cena INTEGER NOT NULL,
            trajanje INTEGER DEFAULT 30
        )
    """)
    
    # Tabela rezervacija
    c.execute("""
        CREATE TABLE IF NOT EXISTS rezervacije (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datum TEXT NOT NULL,
            vreme TEXT NOT NULL,
            ime TEXT NOT NULL,
            telefon TEXT NOT NULL,
            usluga TEXT NOT NULL,
            cena INTEGER NOT NULL,
            trajanje INTEGER DEFAULT 30,
            status TEXT DEFAULT 'zauzet'
        )
    """)
    
    # Ubacivanje podrazumevanih usluga ako je tabela prazna
    c.execute("SELECT COUNT(*) FROM usluge")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO usluge (ime, cena, trajanje) VALUES (?, ?, ?)", [
            ('Šišanje', 1000, 30),
            ('Šišanje + Brada', 1500, 60),
            ('Brada', 600, 30)
        ])
        
    conn.commit()
    conn.close()

init_db()

def get_raspored_za_period(pocetak_str, kraj_str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT datum, vreme, ime, usluga, cena, trajanje, status 
        FROM rezervacije 
        WHERE datum >= ? AND datum <= ?
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
            "trajanje": r["trajanje"] if r["trajanje"] else 30
        }
    return rezultat

@app.route('/api/slobodni_slotovi', methods=['GET'])
def api_slobodni_slotovi():
    datum = request.args.get('datum')
    if not datum:
        return jsonify({'poruka': 'Nedostaje datum'}), 400
        
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT vreme FROM rezervacije WHERE datum = ?", (datum,))
    zauzeti_slotovi = [row['vreme'] for row in c.fetchall()]
    conn.close()
    
    svi_slotovi = []
    start = datetime.strptime("08:00", "%H:%M")
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
    
    # Saznajemo trajanje usluge iz baze
    c.execute("SELECT trajanje FROM usluge WHERE ime = ?", (usluga,))
    u_row = c.fetchone()
    trajanje = u_row['trajanje'] if u_row else 30
    
    c.execute("""
        INSERT INTO rezervacije (datum, vreme, ime, telefon, usluga, cena, trajanje, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'zauzet')
    """, (datum, vreme, ime, telefon, usluga, cena, trajanje))
    
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
