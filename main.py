from flask import request, jsonify
from baza import app

if __name__ == '__main__':
    app.run()
@app.route('/api/naplati', methods=['POST'])
def api_naplati():
    data = request.json
    datum = data.get('datum')
    vreme = data.get('vreme')
    ime = data.get('ime', '')
    usluga = data.get('usluga', '')
    cena = data.get('cena', 0)
    
    # 1. Upisujemo u naplate
    zabelezi_naplatu(datum, vreme, ime, usluga, cena)
    
    # 2. Oslobađamo termin iz rasporeda
    otkazi_termin(datum, vreme)
    
    return jsonify({"status": "ok"})

@app.route('/api/statistika', methods=['GET'])
def api_statistika():
    statistika = uzmi_statistiku_zarade()
    return jsonify(statistika)

if __name__ == "__main__":
    app.run()
