import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

DB_NAME = 'brica.db'

def get_connection():
    return sqlite3.connect(DB_NAME)

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

def get_slotovi_za_datum(datum_str):
    conn = get_connection()
    c = conn.cursor()
    
    # Generiši slotove ako ne postoje za izabrani dan
    c.execute("SELECT COUNT(*) FROM rezervacije WHERE datum=?", (datum_str,))
    if c.fetchone()[0] == 0:
        pocetak = datetime.strptime("09:00", "%H:%M")
        kraj = datetime.strptime("20:00", "%H:%M")
        trenutno = pocetak
        while trenutno < kraj:
            vreme_str = trenutno.strftime("%H:%M")
            c.execute("INSERT INTO rezervacije (datum, vreme, status) VALUES (?, ?, 'slobodan')", (datum_str, vreme_str))
            trenutno += timedelta(minutes=30)
        conn.commit()

    c.execute("SELECT vreme, status, ime, telefon, usluga, cena FROM rezervacije WHERE datum=? ORDER BY vreme", (datum_str,))
    rows = c.fetchall()
    conn.close()
    
    return [{"vreme": r[0], "status": r[1], "ime": r[2], "telefon": r[3], "usluga": r[4], "cena": r[5]} for r in rows]

def get_trajanje_usluge(ime_usluge: str) -> int:
    """Vraća trajanje usluge u minutima iz baze."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT trajanje FROM usluge WHERE ime = ?", (ime_usluge,))
    red = c.fetchone()
    conn.close()
    if red and red[0]:
        return red[0]
    return 30

def zakazi_termin(datum: str, pocetno_vreme: str, ime: str, telefon: str, usluga: str, cena: int, trajanje_minuta: int = 30):
    conn = get_connection()
    c = conn.cursor()
    
    # Prilagođeno slotovima u tvojoj bazi (30 minuta)
    INTERVAL = 30
    broj_slotova = (trajanje_minuta + INTERVAL - 1) // INTERVAL
    
    t_format = "%H:%M"
    pocetno_dt = datetime.strptime(pocetno_vreme, t_format)
    
    # Pravimo listu svih vremena koja ova usluga zauzima
    potrebni_slotovi = []
    for i in range(broj_slotova):
        slot_dt = pocetno_dt + timedelta(minutes=i * INTERVAL)
        potrebni_slotovi.append(slot_dt.strftime(t_format))
    
    try:
        # 1. Proveravamo sve potrebne slotove
        placeholders = ",".join(["?"] * len(potrebni_slotovi))
        c.execute(f"""
            SELECT vreme, status 
            FROM rezervacije 
            WHERE datum = ? AND vreme IN ({placeholders})
        """, [datum] + potrebni_slotovi)
        
        redovi = c.fetchall()
        
        # Ako nema dovoljno slotova do kraja radnog vremena
        if len(redovi) != len(potrebni_slotovi):
            conn.close()
            return False
            
        # Ako je bilo koji od tih slotova već zauzet
        for slot in redovi:
            if slot[1] != 'slobodan':
                conn.close()
                return False
                
        # 2. Ako su SVI slobodni, zauzimamo ih sve odjednom!
        c.execute(f"""
            UPDATE rezervacije 
            SET ime = ?, telefon = ?, usluga = ?, cena = ?, status = 'zakazan'
            WHERE datum = ? AND vreme IN ({placeholders})
        """, [ime, telefon, usluga, cena, datum] + potrebni_slotovi)
        
        conn.commit()
        conn.close()
        return True

    except Exception as e:
        conn.close()
        print("Greška pri zakazivanju:", e)
        return False

# ============================================
# FUNKCIJE ZA UPRAVLJANJE USLUGAMA
# ============================================

def get_sve_usluge():
    """Dohvata sve usluge iz baze"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, ime, cena, trajanje FROM usluge ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "ime": r[1], "cena": r[2], "trajanje": r[3]} for r in rows]

def dodaj_uslugu(ime, cena, trajanje=30):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO usluge (ime, cena, trajanje) VALUES (?, ?, ?)", (ime, cena, trajanje))
    conn.commit()
    novi_id = c.lastrowid
    conn.close()
    return novi_id

def azuriraj_uslugu(usluga_id, nova_cena):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE usluge SET cena=? WHERE id=?", (nova_cena, usluga_id))
    conn.commit()
    conn.close()
    return True

def obrisi_uslugu(usluga_id):
    conn = get_connection()
    c = conn.cursor()
    
    # Proveri da li usluga ima aktivne rezervacije
    c.execute("SELECT ime FROM usluge WHERE id=?", (usluga_id,))
    usluga = c.fetchone()
    if usluga:
        c.execute("SELECT COUNT(*) FROM rezervacije WHERE usluga=? AND status='zakazan'", (usluga[0],))
        broj = c.fetchone()[0]
        if broj > 0:
            conn.close()
            return False, f"Usluga ima {broj} aktivnih rezervacija"
    
    c.execute("DELETE FROM usluge WHERE id=?", (usluga_id,))
    conn.commit()
    conn.close()
    return True, "Usluga obrisana"

# ============================================
# API RUTE ZA ADMIN PANEL
# ============================================

@app.route('/api/usluge', methods=['GET'])
def api_get_usluge():
    """Dohvata sve usluge"""
    try:
        usluge = get_sve_usluge()
        return jsonify(usluge)
    except Exception as e:
        return jsonify({'poruka': str(e)}), 500

@app.route('/api/usluge', methods=['POST'])
def api_dodaj_uslugu():
    """Dodaje novu uslugu"""
    try:
        data = request.get_json()
        ime = data.get('ime')
        cena = data.get('cena')
        trajanje = data.get('trajanje', 30)
        
        # Validacija
        if not ime:
            return jsonify({'poruka': 'Unesite naziv usluge'}), 400
        if not cena or int(cena) <= 0:
            return jsonify({'poruka': 'Unesite ispravnu cenu'}), 400
        
        # Dodaj u bazu
        novi_id = dodaj_uslugu(ime, int(cena), int(trajanje))
        
        return jsonify({
            'id': novi_id,
            'ime': ime,
            'cena': int(cena),
            'trajanje': int(trajanje)
        }), 201
        
    except Exception as e:
        print('GREŠKA pri dodavanju:', e)
        return jsonify({'poruka': str(e)}), 500

@app.route('/api/usluge/<int:id>', methods=['PUT'])
def api_izmeni_uslugu(id):
    """Izmena cene usluge"""
    try:
        data = request.get_json()
        nova_cena = data.get('cena')
        
        if nova_cena is None or int(nova_cena) < 0:
            return jsonify({'poruka': 'Unesite ispravnu cenu'}), 400
        
        azuriraj_uslugu(id, int(nova_cena))
        
        return jsonify({
            'poruka': 'Cena uspešno ažurirana',
            'id': id,
            'cena': int(nova_cena)
        })
        
    except Exception as e:
        print('GREŠKA pri izmeni:', e)
        return jsonify({'poruka': str(e)}), 500

@app.route('/api/usluge/<int:id>', methods=['DELETE'])
def api_obrisi_uslugu(id):
    """Brisanje usluge"""
    try:
        uspesno, poruka = obrisi_uslugu(id)
        if not uspesno:
            return jsonify({'poruka': poruka}), 400
        
        return jsonify({'poruka': poruka, 'id': id})
        
    except Exception as e:
        print('GREŠKA pri brisanju:', e)
        return jsonify({'poruka': str(e)}), 500

# ============================================
# RUTE ZA STRANICE
# ============================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

# ============================================
# POKRETANJE APLIKACIJE
# ============================================

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
