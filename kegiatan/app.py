from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import pytz # Untuk penanganan zona waktu WIB

app = Flask(__name__)
app.secret_key = 'kunci_rahasia_untuk_sesi_yang_sangat_kuat_dan_unik' # Ganti dengan kunci rahasia yang lebih kuat

# Definisikan zona waktu WIB
WIB_TIMEZONE = pytz.timezone('Asia/Jakarta')
UTC_TIMEZONE = pytz.utc

# Fungsi helper untuk mengonversi timestamp UTC dari DB ke string zona waktu lokal (WIB)
def convert_utc_to_wib(utc_timestamp_str):
    if not utc_timestamp_str:
        return ""
    try:
        # Parsing string timestamp UTC dari SQLite (YYYY-MM-DD HH:MM:SS.ffffff)
        if '.' in utc_timestamp_str:
            utc_dt = datetime.strptime(utc_timestamp_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
        else:
            utc_dt = datetime.strptime(utc_timestamp_str, '%Y-%m-%d %H:%M:%S')

        utc_dt = UTC_TIMEZONE.localize(utc_dt)
        wib_dt = utc_dt.astimezone(WIB_TIMEZONE)
        return wib_dt.strftime('%Y-%m-%d %H:%M:%S WIB')
    except ValueError:
        return utc_timestamp_str

# Fungsi untuk mendapatkan koneksi ke database SQLite
def get_db_connection():
    conn = sqlite3.connect('event_registration.db')
    conn.row_factory = sqlite3.Row # Mengembalikan baris sebagai objek mirip dict
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
    conn.execute('''
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,            
            name TEXT NOT NULL,                  
            email TEXT NOT NULL,                 
            nim TEXT NOT NULL,                   
            jurusan TEXT NOT NULL,               
            activity_type TEXT NOT NULL,         
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

# Rute Pendaftaran Pengguna/Registrasi Akun
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']
        nim = request.form['nim']
        jurusan = request.form['jurusan']
        password = request.form['password']

        if not all([email, name, nim, jurusan, password]):
            flash('Semua kolom harus diisi!', 'error')
            return redirect(url_for('register'))
        
        # Validasi format email
        if '@' not in email or '.' not in email:
            flash('Format email tidak valid.', 'error')
            return redirect(url_for('register'))

        # Validasi NIM (wajib 13 angka dan hanya angka)
        if not nim.isdigit() or len(nim) != 13:
            flash('NIM harus 13 digit angka.', 'error')
            return redirect(url_for('register'))
        
        password_hash = generate_password_hash(password)
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (email, name, nim, jurusan, password_hash, is_admin) VALUES (?, ?, ?, ?, ?, ?)', 
                         (email, name, nim, jurusan, password_hash, 0))
            conn.commit()
            flash('Pendaftaran akun berhasil! Silakan masuk.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError as e:
            conn.close()
            if "UNIQUE constraint failed: users.email" in str(e):
                flash('Email ini sudah terdaftar. Silakan gunakan email lain.', 'error')
            elif "UNIQUE constraint failed: users.nim" in str(e):
                flash('NIM ini sudah terdaftar. Silakan gunakan NIM lain.', 'error')
            else:
                flash('Terjadi kesalahan pendaftaran. Coba lagi.', 'error')
            return redirect(url_for('register'))
        finally:
            conn.close()
    return render_template('register.html')

# Rute Login Pengguna
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email_input = request.form['email']
        password = request.form['password']
        if not email_input or not password:
            flash('Email dan password tidak boleh kosong.', 'error')
            return redirect(url_for('login'))

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email_input,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['logged_in'] = True
            session['user_id'] = user['id']        # Simpan ID pengguna
            session['user_email'] = user['email']
            session['user_name'] = user['name']
            session['user_nim'] = user['nim']
            session['user_jurusan'] = user['jurusan']
            session['is_admin'] = user['is_admin']
            flash(f'Selamat datang kembali, {user["name"]}!', 'success')
            return redirect(url_for('index')) # Setelah login, arahkan ke dashboard utama
        else:
            flash('Email atau password salah.', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')

# Rute Logout Pengguna
@app.route('/logout')
def logout():
    session.clear()
    flash('Anda berhasil keluar.', 'success')
    return redirect(url_for('login'))

# Rute Utama/Dashboard Peserta (Menampilkan daftar peserta event)
@app.route('/')
def index():
    if not session.get('logged_in'):
        flash('Anda harus masuk untuk mengakses halaman ini.', 'error')
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    # Mengambil semua peserta event, join dengan tabel users untuk mendapatkan detail NIM dan Jurusan
    participants_raw = conn.execute('''
        SELECT p.id, u.name, u.email, u.nim, u.jurusan, p.activity_type, p.registration_date
        FROM participants p
        JOIN users u ON p.user_id = u.id
        ORDER BY p.registration_date DESC
    ''').fetchall()
    conn.close()

    participants_converted = []
    for participant in participants_raw:
        participant_dict = dict(participant)
        participant_dict['registration_date_wib'] = convert_utc_to_wib(participant_dict['registration_date'])
        participants_converted.append(participant_dict)
    
    return render_template('index.html', participants=participants_converted)

# Rute Form Pendaftaran Event (Bukan registrasi akun)
@app.route('/register_event', methods=['GET', 'POST'])
def register_participant():
    if not session.get('logged_in'):
        flash('Anda harus masuk untuk mendaftar event.', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        activity_type = request.form['activity_type']
        user_id = session['user_id']
        name = session['user_name']
        email = session['user_email']
        nim = session['user_nim']
        jurusan = session['user_jurusan']

        if not activity_type:
            flash('Pilih jenis kegiatan!', 'error')
            return redirect(url_for('register_participant'))
        
        conn = get_db_connection()
        try:
            # Periksa apakah user sudah terdaftar di kegiatan ini
            existing_reg = conn.execute('SELECT * FROM participants WHERE user_id = ? AND activity_type = ?',
                                        (user_id, activity_type)).fetchone()
            if existing_reg:
                flash(f'Anda sudah terdaftar di kegiatan "{activity_type}" ini.', 'error')
                return redirect(url_for('register_participant'))

            conn.execute('INSERT INTO participants (user_id, name, email, nim, jurusan, activity_type) VALUES (?, ?, ?, ?, ?, ?)',
                         (user_id, name, email, nim, jurusan, activity_type))
            conn.commit()
            flash(f'Registrasi event "{activity_type}" berhasil!', 'success')
            return redirect(url_for('index')) # Redirect ke dashboard utama setelah daftar event
        except Exception as e:
            flash(f'Terjadi kesalahan saat mendaftar event: {str(e)}', 'error')
            return redirect(url_for('register_participant'))
        finally:
            conn.close()
    
    # Untuk GET request, tampilkan form pendaftaran event
    return render_template('register_event.html')

# Rute untuk melihat daftar peserta dan total per kegiatan (sama dengan /participants_list)
@app.route('/participants_list') 
def list_participants():
    if not session.get('logged_in'):
        flash('Anda harus masuk untuk melihat daftar peserta.', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    # Mengambil semua peserta event, join dengan tabel users untuk mendapatkan detail NIM dan Jurusan
    participants_raw = conn.execute('''
        SELECT p.id, u.name, u.email, u.nim, u.jurusan, p.activity_type, p.registration_date
        FROM participants p
        JOIN users u ON p.user_id = u.id
        ORDER BY p.registration_date DESC
    ''').fetchall()
    
    participants = []
    for p in participants_raw:
        p_dict = dict(p)
        p_dict['registration_date_wib'] = convert_utc_to_wib(p_dict['registration_date'])
        participants.append(p_dict)

    # Hitung total peserta per kegiatan
    activity_counts_raw = conn.execute('SELECT activity_type, COUNT(*) AS total FROM participants GROUP BY activity_type').fetchall()
    activity_counts = [dict(row) for row in activity_counts_raw]
    
    conn.close()
    return render_template('participants.html', participants=participants, activity_counts=activity_counts)

# Rute Halaman Dashboard Admin
@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        flash('Anda tidak memiliki izin untuk mengakses halaman admin.', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    # Mengambil semua peserta event, join dengan tabel users untuk mendapatkan detail NIM dan Jurusan
    all_participants_raw = conn.execute('''
        SELECT p.id, u.name, u.email, u.nim, u.jurusan, p.activity_type, p.registration_date
        FROM participants p
        JOIN users u ON p.user_id = u.id
        ORDER BY p.registration_date DESC
    ''').fetchall()
    
    # Mengambil semua pengguna sistem
    all_users_raw = conn.execute('SELECT id, email, name, nim, jurusan, is_admin FROM users ORDER BY name ASC').fetchall()
    
    conn.close()

    participants_converted = []
    for p in all_participants_raw:
        p_dict = dict(p)
        p_dict['registration_date_wib'] = convert_utc_to_wib(p_dict['registration_date'])
        participants_converted.append(p_dict)
    
    return render_template('admin_dashboard.html', all_participants=participants_converted, all_users=all_users_raw)


if __name__ == '__main__':
    # Hapus database lama jika ada untuk memulai bersih (khusus development)
    # Anda bisa mengomentari ini untuk menjaga data jika ingin mempertahankan data
    if os.path.exists('event_registration.db'):
        os.remove('event_registration.db')
    
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
