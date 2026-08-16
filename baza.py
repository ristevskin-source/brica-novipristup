import sqlite3
from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime, timedelta
import os

app = Flask(__name__, static_folder='.', static_url_path='')

def get_db_connection():
    conn = sqlite3.connect('baza.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usluge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ime TEXT NOT NULL,
            cena INTEGER NOT NULL,
            trajanje INTEGER DEFAULT 30
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rezervacije (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datum TEXT NOT NULL,
            vreme TEXT NOT NULL,
            ime TEXT NOT NULL,
            telefon TEXT NOT NULL,
            usluga TEXT NOT NULL,
            cena INTEGER NOT NULL,
            naplaceno INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/admin')
def admin():
    return send_from_directory('.', 'admin.html')

# --- USLUGE API ---

@app.route('/api/usluge', methods=['GET', 'POST'])
def api_usluge():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        data = request.get_json()
        ime = data.get('ime')
        cena = data.get('cena')
        trajanje = data.get('trajanje', 30)
        
        cursor.execute('INSERT INTO usluge (ime, cena, trajanje) VALUES (?, ?, ?)', (ime, cena, trajanje))
        conn.commit()
        conn.close()
        return jsonify({"status": "uspesno"})
    
    cursor.execute('SELECT id, ime, cena, trajanje FROM usluge')
    usluge = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(usluge)

@app.route('/api/usluge/<int:id>', methods=['PUT', 'DELETE'])
def api_usluga_id(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'PUT':
        data = request.get_json()
        ime = data.get('ime')
        cena = data.get('cena')
        trajanje = data.get('trajanje', 30)
        
        cursor.execute('UPDATE usluge SET ime = ?, cena = ?, trajanje = ? WHERE id = ?', (ime, cena, trajanje, id))
        conn.commit()
        conn.close()
        return jsonify({"status": "uspesno"})
        
    elif request.method == 'DELETE':
        cursor.execute('DELETE FROM usluge WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "obrisano"})

# --- SLOTOVI I REZERVACIJE API ---

@app.route('/api/slotovi/<datum>')
def api_slotovi(datum):
    d = datetime.strptime(datum, '%Y-%m-%d')
    if d.weekday() == 6: # Nedelja
        return jsonify([])

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT vreme FROM rezervacije WHERE datum = ?', (datum,))
    zauzeti_termini = [row['vreme'] for row in cursor.fetchall()]
    conn.close()

    slotovi = []
    pocetak = 8 * 60
    kraj = 20 * 60
    
    for minutes in range(pocetak, kraj, 30):
        h = minutes // 60
        m = minutes % 60
        vreme_str = f"{h:02d}:{m:02d}"
        
        status = "zauzet" if vreme_str in zauzeti_termini else "slobodan"
        slotovi.append({"vreme": vreme_str, "status": status})

    return jsonify(slotovi)

@app.route('/api/zakazi', methods=['POST'])
def api_zakazi():
    data = request.get_json()
    datum = data.get('datum')
    vreme = data.get('vreme')
    ime = data.get('ime')
    telefon = data.get('telefon')
    usluga = data.get('usluga')
    cena = data.get('cena')

    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM rezervacije WHERE datum = ? AND vreme = ?', (datum, vreme))
    if cursor.fetchone():
        conn.close()
        return jsonify({"poruka": "Termin je već zauzet!"}), 400

    cursor.execute('''
        INSERT INTO rezervacije (datum, vreme, ime, telefon, usluga, cena)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (datum, vreme, ime, telefon, usluga, cena))
    
    conn.commit()
    conn.close()
    return jsonify({"status": "uspesno"})

@app.route('/api/nedelja')
def api_nedelja():
    pocetak = request.args.get('pocetak')
    kraj = request.args.get('kraj')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM rezervacije WHERE datum BETWEEN ? AND ?', (pocetak, kraj))
    rezervacije = [dict(row) for row in cursor.fetchall()]
    conn.close()

    rezultat = {}
    for r in rezervacije:
        datum = r['datum']
        vreme = r['vreme']
        if datum not in rezultat:
            rezultat[datum] = {}
        
        # Pronađi trajanje usluge za ovaj termin
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT trajanje FROM usluge WHERE ime = ?', (r['usluga'],))
        usluga_row = cursor.fetchone()
        conn.close()
        
        trajanje = usluga_row['trajanje'] if usluga_row else 30

        rezultat[datum][vreme] = {
            "ime": r['ime'],
            "usluga": r['usluga'],
            "cena": r['cena'],
            "trajanje": trajanje
        }

    return jsonify(rezultat)

@app.route('/api/otkazi', methods=['POST'])
def api_otkazi():
    data = request.get_json()
    datum = data.get('datum')
    vreme = data.get('vreme')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM rezervacije WHERE datum = ? AND vreme = ?', (datum, vreme))
    conn.commit()
    conn.close()
    return jsonify({"status": "obrisano"})

@app.route('/api/finansije')
def api_finansije():
    od_datuma = request.args.get('od')
    do_datuma = request.args.get('do')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT SUM(cena) as ukupno FROM rezervacije WHERE datum BETWEEN ? AND ?', (od_datuma, do_datuma))
    row = cursor.fetchone()
    conn.close()

    ukupno = row['ukupno'] if row['ukupno'] else 0
    return jsonify({"ukupno": ukupno})

if __name__ == '__main__':
    app.run()
