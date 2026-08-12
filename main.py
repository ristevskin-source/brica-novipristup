@app.post("/api/otkazi")
async def otkazi(data: dict):
    conn = baza.get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE rezervacije 
        SET ime=NULL, telefon=NULL, usluga=NULL, cena=NULL, status='slobodan' 
        WHERE datum=? AND vreme=?
    """, (data['datum'], data['vreme']))
    conn.commit()
    conn.close()
    return {"status": "ok", "poruka": "Termin uspešno otkazan."}
