import sqlite3
from datetime import datetime, timedelta

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

def get_sve_usluge():

def dodaj_uslugu(ime, cena, trajanje=30):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO usluge (ime, cena, trajanje) VALUES (?, ?, ?)", (ime, cena, trajanje))
    conn.commit()
    conn.close()
    return True

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
    c.execute("DELETE FROM usluge WHERE id=?", (usluga_id,))
    conn.commit()
    conn.close()
    return True
