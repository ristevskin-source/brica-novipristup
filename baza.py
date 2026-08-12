import sqlite3
from datetime import datetime, timedelta

DB_NAME = "brica.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS rezervacije (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datum TEXT,
            vreme TEXT,
            ime TEXT,
            telefon TEXT,
            usluga TEXT,
            cena INTEGER,
            status TEXT DEFAULT 'zakazan',
            payment_method TEXT DEFAULT ''
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS usluge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ime TEXT,
            cena INTEGER,
            trajanje INTEGER
        )
    """)
    
    # Unos podrazumevanih usluga ako baza nema ništa
    c.execute("SELECT COUNT(*) FROM usluge")
    if c.fetchone()[0] == 0:
        prazne_usluge = [
            ("Šišanje", 800, 30),
            ("Šišanje + Brada", 1200, 45),
            ("Brada", 500, 20),
            ("Obrve", 400, 15)
        ]
        c.executemany("INSERT INTO usluge (ime, cena, trajanje) VALUES (?, ?, ?)", prazne_usluge)
        
    conn.commit()
    conn.close()

def get_usluge():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT ime, cena, trajanje FROM usluge")
    rows = c.fetchall()
    conn.close()
    return [{"ime": r[0], "cena": r[1], "trajanje": r[2]} for r in rows]

def generisi_slotove_za_dan(datum_str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM rezervacije WHERE datum=?", (datum_str,))
    if c.fetchone()[0] == 0:
        vremena = [
            "09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30",
            "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30",
            "17:00", "17:30", "18:00", "18:30", "19:00", "19:30"
        ]
        for v in vremena:
            c.execute("INSERT INTO rezervacije (datum, vreme, status) VALUES (?, ?, 'slobodan')", (datum_str, v))
        conn.commit()
    conn.close()

def get_slotovi_za_dan(datum_str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT vreme, ime, telefon, usluga, status FROM rezervacije WHERE datum=? ORDER BY vreme ASC", (datum_str,))
    rows = c.fetchall()
    conn.close()
    return [{"vreme": r[0], "ime": r[1], "telefon": r[2], "usluga": r[3], "status": r[4]} for r in rows]

def rezervisi_slotove(datum, vreme, ime, telefon, usluga, cena, trajanje=30):
    conn = get_connection()
    c = conn.cursor()
    
    # Provera slobodnog slota
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
