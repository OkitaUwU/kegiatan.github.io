from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'kunci_rahasia_cadangan_yang_sangat_kuat_dan_unik_jika_error')

# Fungsi untuk mendapatkan koneksi ke database SQLite
def get_db_connection():
    conn = sqlite3.connect('kegiatan_registrasi1.db') 
    conn.row_factory = sqlite3.Row 
    return conn

# Fungsi untuk menginisialisasi database
def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,          
            name TEXT NOT NULL,                  
            nim TEXT NOT NULL UNIQUE,            
            jurusan TEXT NOT NULL,               
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# Rute Pendaftaran Pengguna/Registrasi Akun
@app.route('/register1', methods=['GET', 'POST'])
def register1():
    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']
        nim = request.form['nim']
        jurusan = request.form['jurusan']
        password = request.form['password']

        if not all([email, name, nim, jurusan, password]):
            flash('Semua kolom harus diisi!', 'error')
            return redirect(url_for('register1'))
        
        if '@' not in email or '.' not in email:
            flash('Format email tidak valid.', 'error')
            return redirect(url_for('register1'))

        if not nim.isdigit() or len(nim) != 13:
            flash('NIM harus 13 digit angka.', 'error')
            return redirect(url_for('register1'))
        
        password_hash = generate_password_hash(password)
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (email, name, nim, jurusan, password_hash, is_admin) VALUES (?, ?, ?, ?, ?, ?)', 
                         (email, name, nim, jurusan, password_hash, 0))
            conn.commit()
            flash('Pendaftaran akun berhasil! Silakan masuk.', 'success')
            return redirect(url_for('login1'))
        except sqlite3.IntegrityError as e:
            conn.close()
            if "UNIQUE constraint failed: users.email" in str(e):
                flash('Email ini sudah terdaftar. Silakan gunakan email lain.', 'error')
            elif "UNIQUE constraint failed: users.nim" in str(e):
                flash('NIM ini sudah terdaftar. Silakan gunakan NIM lain.', 'error')
            else:
                flash('Terjadi kesalahan pendaftaran. Coba lagi.', 'error')
            return redirect(url_for('register1'))
        finally:
            conn.close()
    return render_template('register1.html')

# Rute Login Pengguna
@app.route('/login1', methods=['GET', 'POST'])
def login1():
    if request.method == 'POST':
        email_input = request.form['email']
        password = request.form['password']
        if not email_input or not password:
            flash('Email dan password tidak boleh kosong.', 'error')
            return redirect(url_for('login1'))

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email_input,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['logged_in'] = True
            session['user_id'] = user['id']        
            session['user_email'] = user['email']
            session['user_name'] = user['name']
            session['user_nim'] = user['nim']
            session['user_jurusan'] = user['jurusan']
            session['is_admin'] = user['is_admin']
            flash(f'Selamat datang kembali, {user["name"]}!', 'success')
            return redirect(url_for('index1')) 
        else:
            flash('Email atau password salah.', 'error')
            return redirect(url_for('login1'))
    return render_template('login1.html')

# Rute Utama/Dashboard Peserta
@app.route('/index1')
def index1():
    if not session.get('logged_in'):
        flash('Anda harus masuk untuk mengakses halaman ini.', 'error')
        return redirect(url_for('login1'))
        
    return render_template('index1.html')


# Rute Logout Pengguna
@app.route('/logout1')
def logout1():
    session.clear()
    flash('Anda berhasil keluar.', 'success')
    return redirect(url_for('login1'))

if __name__ == '__main__':
    # Hapus database lama jika ada untuk memulai bersih (khusus development)
    if os.path.exists('kegiatan_registrasi1.db'): 
        os.remove('kegiatan_registrasi1.db') 
    
    init_db()
    
    conn = get_db_connection()
    # Buat pengguna admin default
    admin_user = conn.execute("SELECT * FROM users WHERE email = 'admin@example.com'").fetchone()
    if not admin_user:
        hashed_admin_password = generate_password_hash('admin123')
        conn.execute('INSERT INTO users (email, name, nim, jurusan, password_hash, is_admin) VALUES (?, ?, ?, ?, ?, ?)', 
                     ('admin@example.com', 'Administrator', '1234567890123', 'Informatika', hashed_admin_password, 1))
        conn.commit()
        print("Pengguna admin default telah dibuat dengan email: 'admin@example.com', NIM: '1234567890123' dan password: 'admin123'")
    conn.close()

    app.run(debug=True)
