import sqlite3
from datetime import datetime, timedelta

DB_NAME = 'brica.db'

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Tabela usluga
    c.execute('''
        CREATE TABLE IF NOT EXISTS usluge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ime TEXT NOT NULL,
            cena INTEGER NOT NULL,
            trajanje INTEGER NOT NULL
        )
    ''')
    
    # Podrazumevane usluge ako je tabela prazna
    c.execute("SELECT COUNT(*) FROM usluge")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO usluge (ime, cena, trajanje) VALUES ('Šišanje', 1000, 30)")
        c.execute("INSERT INTO usluge (ime, cena, trajanje) VALUES ('Breda / Brijanje', 600, 30)")
        c.execute("INSERT INTO usluge (ime, cena, trajanje) VALUES ('Šišanje + Brada', 1500, 45)")

    # Tabela rezervacija
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

def get_usluge():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, ime, cena, trajanje FROM usluge")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "ime": r[1], "cena": r[2], "trajanje": r[3]} for r in rows]

def dodaj_uslugu(ime, cena, trajanje):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO usluge (ime, cena, trajanje) VALUES (?, ?, ?)", (ime, cena, trajanje))
    conn.commit()
    conn.close()

def obrisi_uslugu(usluga_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM usluge WHERE id=?", (usluga_id,))
    conn.commit()
    conn.close()

def generisi_slotove_za_dan(datum_str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM rezervacije WHERE datum=?", (datum_str,))
    if c.fetchone()[0] == 0:
        pocetak = datetime.strptime("09:00", "%H:%M")
        kraj = datetime.strptime("17:00", "%H:%M")
        trenutno = pocetak
        while trenutno < kraj:
            vreme_str = trenutno.strftime("%H:%M")
            c.execute("INSERT INTO rezervacije (datum, vreme, status) VALUES (?, ?, 'slobodan')", (datum_str, vreme_str))
            trenutno += timedelta(minutes=30)
        conn.commit()
    conn.close()

def get_slotovi_za_dan(datum_str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT vreme, status, ime, telefon, usluga, cena FROM rezervacije WHERE datum=? ORDER BY vreme", (datum_str,))
    rows = c.fetchall()
    conn.close()
    return [{"vreme": r[0], "status": r[1], "ime": r[2], "telefon": r[3], "usluga": r[4], "cena": r[5]} for r in rows]

def rezervisi_slotove(datum, vreme, ime, telefon, usluga, cena, trajanje=30):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT status FROM rezervacije WHERE datum=? AND vreme=?", (datum, vreme))
    res = c.fetchone()
    if not res or res[0] != 'slobodan':
        conn.close()
        return False
        
    c.execute("""
        UPDATE rezervacije 
        SET ime=?, telefon=?, usluga=?, cena=?, status='zakazan' 
        WHERE datum=? AND vreme=?
    """, (ime, telefon, usluga, cena, datum, vreme))
    
    conn.commit()
    conn.close()
    return True
