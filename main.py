from flask import request, jsonify
from baza import app, zabelezi_naplatu, uzmi_statistiku_zarade, get_connection

@app.route('/api/naplati', methods=['POST'])
def api_naplati():
    data = request.json
    datum, vreme, ime, usluga, cena = data.get('datum'), data.get('vreme'), data.get('ime', ''), data.get('usluga', ''), data.get('cena', 0)
    zabelezi_naplatu(datum, vreme, ime, usluga, cena)
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM rezervacije WHERE datum = ? AND vreme = ?", (datum, vreme))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/statistika', methods=['GET'])
def api_statistika():
    return jsonify(uzmi_statistiku_zarade())

if __name__ == "__main__":
    app.run()
