from flask import request, jsonify
from baza import app, zabelezi_naplatu, uzmi_statistiku_zarade, get_connection

@app.route('/api/naplati', methods=['POST'])
def api_naplati():
    data = request.json
    datum = data.get('datum')
    vreme = data.get('vreme')
    ime = data.get('ime', '')
    usluga = data.get('usluga', '')
    cena = data.get('cena', 0)
    
    # 1. Beležimo zaradu
    zabelezi_naplatu(datum, vreme, ime, usluga, cena)
    
    # 2. Brišemo termin iz baze
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM rezervacije WHERE datum = ? AND vreme = ?", (datum, vreme))
    conn.commit()
    conn.close()
    
    return jsonify({"status": "ok"})

@app.route('/api/statistika', methods=['GET'])
def api_statistika():
    statistika = uzmi_statistiku_zarade()
    return jsonify(statistika)

if __name__ == "__main__":
    app.run()
