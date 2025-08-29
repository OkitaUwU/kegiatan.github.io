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

# Data kegiatan yang sudah disediakan
ACTIVITIES = {
    "Kelas Catur": {
        "description": "Pelajari strategi catur dari dasar hingga mahir.",
        "day_time": "Setiap Selasa, 16:00 - 18:00 WIB",
        "image": "https://seputarpapua.com/wp-content/uploads/2023/11/Percasi-Mimika-Pertandingkan-Catur-Kelas-Junior-dan-Senior.webp" # Warna disesuaikan
    },
    "Futsal": {
        "description": "Bergabung dalam tim futsal dan tingkatkan skill Anda.",
        "day_time": "Setiap Rabu, 19:00 - 21:00 WIB",
        "image": "https://jasakontraktorlapangan.id/wp-content/uploads/2023/02/Jasa-Pembuatan-Lapangan-Futsal-Serang.jpeg" # Warna disesuaikan
    },
    "Kelas Memasak": {
        "description": "Eksplorasi resep-resep kuliner populer dan ciptakan hidangan lezat.",
        "day_time": "Setiap Kamis, 14:00 - 16:00 WIB",
        "image": "https://www.joyful-cooking.com/uploads/6/3/3/5/63359151/dscf9643_orig.jpg" # Warna disesuaikan
    },
    "Kelas Musik": {
        "description": "Belajar instrumen favorit atau vokal dengan instruktur profesional.",
        "day_time": "Setiap Jumat, 17:00 - 19:00 WIB",
        "image": "https://interiorqu.id/wp-content/uploads/2022/10/IMG-20220702-WA0026.jpg" # Warna disesuaikan
    },
    "Voli": {
        "description": "Gabung tim voli dan latih kemampuan spikes dan blocks.",
        "day_time": "Setiap Sabtu, 10:00 - 12:00 WIB",
        "image": "https://www.lantai-kayu.co.id/wp-content/uploads/2022/03/lapang-voli-outdoor.jpg" # Warna disesuaikan
    },
    "Badminton": {
        "description": "Asah kelincahan Anda di lapangan badminton.",
        "day_time": "Setiap Minggu, 09:00 - 11:00 WIB",
        "image": "https://percepat.com/wp-content/uploads/2019/04/Ukuran-Lapangan-Bulu-Tangkis-1.jpg" # Warna disesuaikan
    },
    "Kelas Tari": {
        "description": "Ekspresikan diri melalui berbagai genre tarian.",
        "day_time": "Setiap Senin, 15:00 - 17:00 WIB",
        "image": "https://galuhaprilina.wordpress.com/wp-content/uploads/2017/08/a8faf-annex-studio-e.jpg" # Warna disesuaikan
    }
}


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
    conn = sqlite3.connect('kegiatan_registrasi.db') # NAMA DATABASE BERUBAH
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

# Rute Utama/Dashboard Peserta (Menampilkan daftar pendaftaran kegiatan user tersebut)
@app.route('/')
def index():
    if not session.get('logged_in'):
        flash('Anda harus masuk untuk mengakses halaman ini.', 'error')
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    # Mengambil pendaftaran kegiatan khusus untuk user yang sedang login
    user_id = session['user_id']
    participants_raw = conn.execute('''
        SELECT p.id, u.name, u.email, u.nim, u.jurusan, p.activity_type, p.registration_date
        FROM participants p
        JOIN users u ON p.user_id = u.id
        WHERE p.user_id = ?
        ORDER BY p.registration_date DESC
    ''', (user_id,)).fetchall() # Filter berdasarkan user_id
    conn.close()

    participants_converted = []
    for participant in participants_raw:
        participant_dict = dict(participant)
        participant_dict['registration_date_wib'] = convert_utc_to_wib(participant_dict['registration_date'])
        participants_converted.append(participant_dict)
    
    return render_template('index.html', participants=participants_converted)


# Rute untuk melihat semua kegiatan dan mendaftar
@app.route('/activities')
def browse_activities():
    if not session.get('logged_in'):
        flash('Anda harus masuk untuk melihat kegiatan.', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    # Hitung total peserta per kegiatan
    activity_counts_raw = conn.execute('SELECT activity_type, COUNT(*) AS total FROM participants GROUP BY activity_type').fetchall()
    activity_counts_dict = {row['activity_type']: row['total'] for row in activity_counts_raw}
    conn.close()

    # Gabungkan data ACTIVITIES dengan jumlah peserta
    activities_with_counts = {}
    for name, data in ACTIVITIES.items():
        activities_with_counts[name] = {
            **data, # Salin semua data dari ACTIVITIES
            "participant_count": activity_counts_dict.get(name, 0) # Tambahkan jumlah peserta, default 0
        }

    return render_template('activities_browse.html', activities=activities_with_counts)


# Rute Form Pendaftaran Kegiatan (Bukan registrasi akun)
@app.route('/register_kegiatan', methods=['GET', 'POST']) # NAMA RUTE BERUBAH
def register_kegiatan(): # NAMA FUNGSI BERUBAH
    if not session.get('logged_in'):
        flash('Anda harus masuk untuk mendaftar kegiatan.', 'error')
        return redirect(url_for('login'))

    # Ambil activity_name dari parameter URL jika GET request, atau dari form jika POST
    activity_name_from_param = request.args.get('activity_name')
    
    if request.method == 'POST':
        activity_type = request.form.get('activity_type') # Ambil dari hidden input di form
        
        if not activity_type:
            flash('Pilih jenis kegiatan yang valid!', 'error')
            return redirect(url_for('browse_activities')) # Kembali ke browse jika tidak ada kegiatan

        user_id = session['user_id']
        name = session['user_name']
        email = session['user_email']
        nim = session['user_nim']
        jurusan = session['user_jurusan']

        conn = get_db_connection()
        try:
            # Periksa apakah user sudah terdaftar di kegiatan ini
            existing_reg = conn.execute('SELECT * FROM participants WHERE user_id = ? AND activity_type = ?',
                                        (user_id, activity_type)).fetchone()
            if existing_reg:
                flash(f'Anda sudah terdaftar di kegiatan "{activity_type}" ini.', 'error')
                return redirect(url_for('index')) # Kembali ke dashboard jika sudah terdaftar

            conn.execute('INSERT INTO participants (user_id, name, email, nim, jurusan, activity_type) VALUES (?, ?, ?, ?, ?, ?)',
                         (user_id, name, email, nim, jurusan, activity_type))
            conn.commit()
            flash(f'Registrasi kegiatan "{activity_type}" berhasil!', 'success')
            return redirect(url_for('index')) # Redirect ke dashboard utama setelah daftar kegiatan
        except Exception as e:
            flash(f'Terjadi kesalahan saat mendaftar kegiatan: {str(e)}', 'error')
            return redirect(url_for('browse_activities')) # Kembali ke browse jika ada error
        finally:
            conn.close()
    
    # Untuk GET request (dari halaman browse_activities)
    if activity_name_from_param and activity_name_from_param in ACTIVITIES:
        return render_template('register_kegiatan.html', activity_name=activity_name_from_param) # NAMA TEMPLATE BERUBAH
    else:
        # Jika tidak ada activity_name yang valid, arahkan ke halaman browse
        flash('Pilih kegiatan terlebih dahulu.', 'info')
        return redirect(url_for('browse_activities'))


# Rute untuk melihat SEMUA daftar peserta dan total per kegiatan (untuk admin/public view)
@app.route('/participants_list') 
def list_participants():
    if not session.get('logged_in'):
        flash('Anda harus masuk untuk melihat daftar peserta.', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    # Mengambil semua peserta kegiatan, join dengan tabel users untuk mendapatkan detail NIM dan Jurusan
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
    # Mengambil semua peserta kegiatan, join dengan tabel users untuk mendapatkan detail NIM dan Jurusan
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
    if os.path.exists('kegiatan_registrasi.db'): # NAMA DATABASE BERUBAH
        os.remove('kegiatan_registrasi.db') # NAMA DATABASE BERUBAH
    
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
