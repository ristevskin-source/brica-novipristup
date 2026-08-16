import sqlite3
from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime, timedelta
import os

app = Flask(__name__, static_folder='.', static_url_path='')

def get_db_connimport sqlite3
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

# Generišemo standardne radne termine od 09:00 do 20:00 na 30 min
svi_slotovi = []
start = datetime.strptime("09:00", "%H:%M")
end = datetime.strptime("20:00", "%H:%M")

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
@app.route('/api/usluge', methods=['GET', 'POST'])
def api_usluge():
conn = get_connection()
c = conn.cursor()
    if request.method == 'PUT':
        data = request.get_json()
        nova_cena = data.get('cena')
        c.execute("UPDATE usluge SET cena = ? WHERE id = ?", (nova_cena, id))
        conn.commit()
    if request.method == 'GET':
        c.execute("SELECT * FROM usluge")
        usluge = [dict(row) for row in c.fetchall()]
conn.close()
        return jsonify({'status': 'ok'})
    elif request.method == 'DELETE':
        c.execute("DELETE FROM usluge WHERE id = ?", (id,))
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
app.run(debug=True, port=5000)ection():
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
