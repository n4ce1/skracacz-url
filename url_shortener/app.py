from flask import Flask, request, redirect, render_template, send_file, abort
import sqlite3, os, string, random
import qrcode

app = Flask(__name__)
DB_NAME = 'urls.db'
QR_DIR = 'static/qrcodes'

os.makedirs(QR_DIR, exist_ok=True)

# Inicjalizacja bazy danych
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS urls (
                short TEXT PRIMARY KEY,
                full TEXT NOT NULL
            )
        ''')

def generate_short_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        full_url = request.form['url']
        custom_alias = request.form.get('alias', '').strip()

        short_code = custom_alias if custom_alias else generate_short_code()

        # Sprawdź, czy alias już istnieje
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.execute("SELECT short FROM urls WHERE short = ?", (short_code,))
            if cur.fetchone():
                return f"Alias '{short_code}' już istnieje. Wybierz inny.", 400

            conn.execute("INSERT INTO urls (short, full) VALUES (?, ?)", (short_code, full_url))

        short_url = request.host_url + short_code
        qr_filename = f"{short_code}.png"
        qr_path = os.path.join(QR_DIR, qr_filename)
        qrcode.make(short_url).save(qr_path)
        return render_template('index.html', short_url=short_url, qr_code=f"/{QR_DIR}/{qr_filename}")
    return render_template('index.html')

@app.route('/manage', methods=['GET', 'POST'])
def manage():
    if request.method == 'POST':
        # Obsługa usuwania
        to_delete = request.form.get('delete')
        if to_delete:
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("DELETE FROM urls WHERE short = ?", (to_delete,))
                qr_path = os.path.join(QR_DIR, f"{to_delete}.png")
                if os.path.exists(qr_path):
                    os.remove(qr_path)

    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.execute("SELECT short, full FROM urls")
        links = cur.fetchall()

    return render_template('manage.html', links=links, host_url=request.host_url)

@app.route('/<short>')
def redirect_short(short):
    # Zabezpieczenie, by nie przekierowywać na /manage itp.
    if short in ['favicon.ico', 'manage']:
        abort(404)

    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.execute("SELECT full FROM urls WHERE short = ?", (short,))
        row = cur.fetchone()
        if row:
            return redirect(row[0])
    return "Link nie istnieje.", 404

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
