from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
from datetime import datetime, timedelta
import math

DB_PATH = 'termini.db'

app = Flask(__name__)
CORS(app)

WORK_START = datetime.strptime("09:00", "%H:%M").time()
WORK_END = datetime.strptime("20:00", "%H:%M").time()
PAUSE_START = datetime.strptime("13:00", "%H:%M").time()
PAUSE_END = datetime.strptime("14:00", "%H:%M").time()
SLOT_MINUTES = 15


def get_db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/api/usluge')
def api_usluge():
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT rowid as id, usluga as ime, cena, trajanje FROM cenovnik ORDER BY trajanje ASC")
    rows = c.fetchall()
    conn.close()
    usluge = [dict(r) for r in rows]
    return jsonify(usluge)


def time_add_minutes(time_str, minutes):
    t = datetime.strptime(time_str, "%H:%M")
    t += timedelta(minutes=minutes)
    return t.strftime("%H:%M")


def generate_day_slots():
    slots = []
    t = datetime.strptime("09:00", "%H:%M")
    end = datetime.strptime("20:00", "%H:%M")
    while t < end:
        time_str = t.strftime("%H:%M")
        # skip pause range
        if not (PAUSE_START <= t.time() < PAUSE_END):
            slots.append(time_str)
        t += timedelta(minutes=SLOT_MINUTES)
    return slots


@app.route('/api/slotovi/<datum>')
def api_slotovi(datum):
    # datum expected in YYYY-MM-DD
    try:
        datetime.strptime(datum, "%Y-%m-%d")
    except Exception:
        return jsonify({'error': 'Neispravan format datuma. Očekivano YYYY-MM-DD'}), 400

    conn = get_db_conn()
    c = conn.cursor()

    # fetch reservations for date
    c.execute("SELECT id, vreme, ime, telefon, usluga, cena FROM rezervacije WHERE datum=?", (datum,))
    rezervacije = {row['vreme']: dict(row) for row in c.fetchall()}

    # build slots based on working schedule
    slots = []
    all_slots = generate_day_slots()

    for vreme in all_slots:
        if PAUSE_START.strftime("%H:%M") <= vreme < PAUSE_END.strftime("%H:%M"):
            slots.append({'vreme': vreme, 'status': 'pauza'})
            continue

        r = rezervacije.get(vreme)
        if r and r.get('ime'):
            slots.append({'vreme': vreme, 'status': 'zauzet', 'ime': r.get('ime'), 'telefon': r.get('telefon'), 'rezervacija_id': r.get('id')})
        else:
            slots.append({'vreme': vreme, 'status': 'slobodan'})

    conn.close()
    return jsonify(slots)


def slots_for_service(start_time_str, duration_minutes):
    # returns list of time strings starting from start_time_str covering duration
    count = math.ceil(duration_minutes / SLOT_MINUTES)
    slots = [start_time_str]
    t = datetime.strptime(start_time_str, "%H:%M")
    for i in range(1, count):
        t += timedelta(minutes=SLOT_MINUTES)
        slots.append(t.strftime("%H:%M"))
    return slots


@app.route('/api/zakazi', methods=['POST'])
def api_zakazi():
    data = request.get_json() or {}
    required = ['datum', 'vreme', 'ime', 'telefon']
    for r in required:
        if not data.get(r):
            return jsonify({'status': 'error', 'poruka': f'Nedostaje polje {r}'}), 400

    datum = data['datum']
    vreme = data['vreme']
    ime = data['ime'].strip()
    telefon = data['telefon'].strip()

    # Determine service by name or id
    usluga_input = data.get('usluga')
    cena_input = data.get('cena')

    conn = get_db_conn()
    c = conn.cursor()

    # find service in cenovnik
    if usluga_input is None and cena_input is None:
        conn.close()
        return jsonify({'status': 'error', 'poruka': 'Nedostaje usluga'}), 400

    # try to find by exact name
    c.execute("SELECT usluga, cena, trajanje FROM cenovnik WHERE usluga = ?", (usluga_input,))
    svc = c.fetchone()
    if not svc:
        # try by id if provided
        try:
            svc_id = int(data.get('usluga_id'))
            c.execute("SELECT usluga, cena, trajanje FROM cenovnik WHERE rowid = ?", (svc_id,))
            svc = c.fetchone()
        except Exception:
            svc = None

    if not svc:
        # fallback: use provided cena and assume 15 minutes
        trajanje = int(data.get('trajanje', 15))
        cena = int(cena_input) if cena_input else 0
        usluga_ime = usluga_input or 'Usluga'
    else:
        usluga_ime = svc['usluga']
        cena = svc['cena']
        trajanje = svc['trajanje']

    # validate time not in pause
    t_obj = datetime.strptime(vreme, "%H:%M").time()
    if PAUSE_START <= t_obj < PAUSE_END:
        conn.close()
        return jsonify({'status': 'error', 'poruka': 'Izabrano vreme je u pauzi'}), 400

    # compute required slots
    potrebni_slotovi = slots_for_service(vreme, trajanje)

    # check within working hours
    if datetime.strptime(potrebni_slotovi[-1], "%H:%M").time() > WORK_END:
        conn.close()
        return jsonify({'status': 'error', 'poruka': 'Usluga prevazilazi radno vreme'}), 400

    # check availability
    conflicts = []
    for s in potrebni_slotovi:
        # if s in pause
        t_check = datetime.strptime(s, "%H:%M").time()
        if PAUSE_START <= t_check < PAUSE_END:
            conflicts.append(s)
            break
        c.execute("SELECT id, ime FROM rezervacije WHERE datum=? AND vreme=?", (datum, s))
        row = c.fetchone()
        if row and row['ime']:
            conflicts.append(s)

    if conflicts:
        conn.close()
        return jsonify({'status': 'error', 'poruka': 'Nema dovoljno slobodnih termina', 'conflicts': conflicts}), 400

    # reserve: update existing rows if present, otherwise insert
    try:
        prvi = True
        for s in potrebni_slotovi:
            c.execute("SELECT id FROM rezervacije WHERE datum=? AND vreme=?", (datum, s))
            row = c.fetchone()
            if row:
                # update
                if prvi:
                    cena_slot = cena
                else:
                    cena_slot = 0
                c.execute("UPDATE rezervacije SET ime=?, telefon=?, usluga=?, cena=?, status='zakazan' WHERE id=?",
                          (ime, telefon, usluga_ime, cena_slot, row['id']))
            else:
                # insert
                if prvi:
                    cena_slot = cena
                else:
                    cena_slot = 0
                c.execute("INSERT INTO rezervacije (usluga, datum, vreme, ime, telefon, cena, status) VALUES (?,?,?,?,?,?,?)",
                          (usluga_ime, datum, s, ime, telefon, cena_slot, 'zakazan'))
            prvi = False
        conn.commit()
        return jsonify({'status': 'ok'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'poruka': str(e)}), 500
    finally:
        conn.close()


if __name__ == '__main__':
    print('Starting API server on http://127.0.0.1:5000')
    app.run(debug=True)
