from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import pytz # Untuk penanganan zona waktu WIB
import json # Untuk menyimpan list kegiatan sebagai JSON string

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
        "image": "https://seputarpapua.com/wp-content/uploads/2023/11/Percasi-Mimika-Pertandingkan-Catur-Kelas-Junior-dan-Senior.webp"
    },
    "Futsal": {
        "description": "Bergabung dalam tim futsal dan tingkatkan skill Anda.",
        "day_time": "Setiap Rabu, 19:00 - 21:00 WIB",
        "image": "https://jasakontraktorlapangan.id/wp-content/uploads/2023/02/Jasa-Pembuatan-Lapangan-Futsal-Serang.jpeg"
    },
    "Kelas Memasak": {
        "description": "Eksplorasi resep-resep kuliner populer dan ciptakan hidangan lezat.",
        "day_time": "Setiap Kamis, 14:00 - 16:00 WIB",
        "image": "https://www.joyful-cooking.com/uploads/6/3/3/5/63359151/dscf9643_orig.jpg"
    },
    "Kelas Musik": {
        "description": "Belajar instrumen favorit atau vokal dengan instruktur profesional.",
        "day_time": "Setiap Jumat, 17:00 - 19:00 WIB",
        "image": "https://interiorqu.id/wp-content/uploads/2022/10/IMG-20220702-WA0026.jpg"
    },
    "Voli": {
        "description": "Gabung tim voli dan latih kemampuan spikes dan blocks.",
        "day_time": "Setiap Sabtu, 10:00 - 12:00 WIB",
        "image": "https://www.lantai-kayu.co.id/wp-content/uploads/2022/03/lapang-voli-outdoor.jpg"
    },
    "Badminton": {
        "description": "Asah kelincahan Anda di lapangan badminton.",
        "day_time": "Setiap Minggu, 09:00 - 11:00 WIB",
        "image": "https://percepat.com/wp-content/uploads/2019/04/Ukuran-Lapangan-Bulu-Tangkis-1.jpg"
    },
    "Kelas Tari": {
        "description": "Ekspresikan diri melalui berbagai genre tarian.",
        "day_time": "Setiap Senin, 15:00 - 17:00 WIB",
        "image": "https://galuhaprilina.wordpress.com/wp-content/uploads/2017/08/a8faf-annex-studio-e.jpg"
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
    conn = sqlite3.connect('kegiatan_registrasi.db') 
    conn.row_factory = sqlite3.Row 
    return conn

# Fungsi untuk menginisialisasi database
def init_db():
    conn = get_db_connection()
    # Perubahan di sini: NIM dan Jurusan tidak lagi NOT NULL
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,          
            name TEXT NOT NULL,                  
            nim TEXT UNIQUE,            
            jurusan TEXT,               
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    # Tabel baru untuk menyimpan pilihan final kegiatan setiap pengguna
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_final_selection (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE, -- Setiap user hanya bisa membuat 1 pilihan final
            selected_activities TEXT NOT NULL, -- Disimpan sebagai JSON string: '["Kelas Catur", "Futsal"]'
            submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
            session['user_id'] = user['id']        
            session['user_email'] = user['email']
            session['user_name'] = user['name']
            session['user_nim'] = user['nim']
            session['user_jurusan'] = user['jurusan']
            session['is_admin'] = user['is_admin']
            
            # Perubahan di sini: Arahkan admin ke dashboard admin
            if user['is_admin'] == 1:
                flash(f'Selamat datang kembali, Administrator!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash(f'Selamat datang kembali, {user["name"]}!', 'success')
                return redirect(url_for('index')) 
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

# Rute Utama/Dashboard Peserta
@app.route('/')
def index():
    if not session.get('logged_in'):
        flash('Anda harus masuk untuk mengakses halaman ini.', 'error')
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    user_id = session['user_id']
    
    # Ambil pilihan final user dari tabel user_final_selection
    user_selection_raw = conn.execute('''
        SELECT * FROM user_final_selection WHERE user_id = ?
    ''', (user_id,)).fetchone()
    conn.close()

    user_selection = None
    if user_selection_raw:
        user_selection = dict(user_selection_raw)
        user_selection['selected_activities'] = json.loads(user_selection['selected_activities'])
        user_selection['submission_date_wib'] = convert_utc_to_wib(user_selection['submission_date'])
    
    return render_template('index.html', user_selection=user_selection)


# Rute untuk melihat semua kegiatan dan mendaftar
@app.route('/activities')
def browse_activities():
    if not session.get('logged_in'):
        flash('Anda harus masuk untuk melihat kegiatan.', 'error')
        return redirect(url_for('login'))

    # Pengecekan jika pengguna adalah admin
    if session.get('is_admin'):
        flash('Admin tidak dapat mendaftar kegiatan.', 'info')
        return redirect(url_for('index'))

    conn = get_db_connection()
    user_id = session['user_id']

    # Cek apakah user sudah membuat pilihan final
    has_made_selection = conn.execute('SELECT 1 FROM user_final_selection WHERE user_id = ?', (user_id,)).fetchone() is not None
    user_selected_activities = []
    if has_made_selection:
        selection_data = conn.execute('SELECT selected_activities FROM user_final_selection WHERE user_id = ?', (user_id,)).fetchone()
        if selection_data:
            user_selected_activities = json.loads(selection_data['selected_activities'])

    # Hitung total peserta per kegiatan dari user_final_selection
    all_selections_raw = conn.execute('SELECT selected_activities FROM user_final_selection').fetchall()
    
    activity_counts_dict = {activity_name: 0 for activity_name in ACTIVITIES.keys()}
    for selection_entry in all_selections_raw:
        try:
            selected_activities_list = json.loads(selection_entry['selected_activities'])
            for activity in selected_activities_list:
                if activity in activity_counts_dict:
                    activity_counts_dict[activity] += 1
        except json.JSONDecodeError:
            # Handle error if JSON is malformed in DB
            pass

    # Gabungkan data ACTIVITIES dengan jumlah peserta
    activities_with_counts = {}
    for name, data in ACTIVITIES.items():
        activities_with_counts[name] = {
            **data, 
            "participant_count": activity_counts_dict.get(name, 0)
        }
    conn.close()

    return render_template('activities_browse.html', 
                           activities=activities_with_counts, 
                           has_made_selection=has_made_selection,
                           user_selected_activities=user_selected_activities)


# Rute Konfirmasi Pilihan Kegiatan
@app.route('/confirm_selection', methods=['GET', 'POST']) 
def confirm_selection(): 
    if not session.get('logged_in'):
        flash('Anda harus masuk untuk mendaftar kegiatan.', 'error')
        return redirect(url_for('login'))

    # Pengecekan jika pengguna adalah admin
    if session.get('is_admin'):
        flash('Admin tidak dapat mendaftar kegiatan.', 'info')
        return redirect(url_for('index'))

    user_id = session['user_id']
    conn = get_db_connection()
    # Cek lagi apakah user sudah membuat pilihan final
    has_made_selection = conn.execute('SELECT 1 FROM user_final_selection WHERE user_id = ?', (user_id,)).fetchone() is not None
    conn.close()

    if has_made_selection:
        flash('Anda sudah membuat pilihan kegiatan final dan tidak bisa mendaftar lagi.', 'info')
        return redirect(url_for('index'))

    if request.method == 'GET':
        selected_activities = request.args.getlist('selected_activities')
        
        if not selected_activities:
            flash('Anda belum memilih kegiatan apapun.', 'error')
            return redirect(url_for('browse_activities'))

        if not (1 <= len(selected_activities) <= 3):
            flash('Anda harus memilih antara 1 hingga 3 kegiatan.', 'error')
            return redirect(url_for('browse_activities'))
        
        # Simpan pilihan sementara di session untuk konfirmasi POST
        session['temp_selected_activities'] = selected_activities
        return render_template('confirm_selection.html', selected_activities=selected_activities)

    elif request.method == 'POST':
        # Ambil pilihan dari hidden input di form konfirmasi
        selected_activities = request.form.getlist('selected_activities')
        
        # Validasi ulang
        if not selected_activities or not (1 <= len(selected_activities) <= 3):
            flash('Kesalahan validasi pilihan kegiatan. Silakan pilih kembali.', 'error')
            return redirect(url_for('browse_activities'))

        user_id = session['user_id']
        conn = get_db_connection()
        try:
            # Cek duplikasi terakhir sebelum insert (race condition protection)
            existing_selection = conn.execute('SELECT 1 FROM user_final_selection WHERE user_id = ?', (user_id,)).fetchone()
            if existing_selection:
                flash('Anda sudah membuat pilihan kegiatan final dan tidak bisa mendaftar lagi.', 'info')
                return redirect(url_for('index'))

            # Simpan pilihan final sebagai JSON string
            json_activities = json.dumps(selected_activities)
            conn.execute('INSERT INTO user_final_selection (user_id, selected_activities) VALUES (?, ?)',
                         (user_id, json_activities))
            conn.commit()
            flash('Pilihan kegiatan Anda berhasil dikonfirmasi dan disimpan!', 'success')
            session.pop('temp_selected_activities', None) # Hapus pilihan sementara
            return redirect(url_for('index'))
        except sqlite3.IntegrityError as e:
            # Ini akan tertangkap jika UNIQUE constraint failed karena suatu alasan (misal: refresh page yang cepat)
            flash('Terjadi kesalahan: Anda sudah membuat pilihan kegiatan final.', 'error')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Terjadi kesalahan saat menyimpan pilihan: {str(e)}', 'error')
            return redirect(url_for('browse_activities'))
        finally:
            conn.close()


# Rute untuk melihat SEMUA daftar peserta dan total per kegiatan (untuk admin/public view)
@app.route('/participants_list') 
def list_participants():
    if not session.get('logged_in'):
        flash('Anda harus masuk untuk melihat daftar peserta.', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    # Mengambil semua pilihan final, join dengan tabel users untuk detail
    all_selections_raw = conn.execute('''
        SELECT ufs.id, u.name AS user_name, u.nim, u.jurusan, ufs.selected_activities, ufs.submission_date
        FROM user_final_selection ufs
        JOIN users u ON ufs.user_id = u.id
        WHERE u.is_admin = 0 -- Perubahan di sini: Hanya sertakan pengguna yang bukan admin
        ORDER BY ufs.submission_date DESC
    ''').fetchall()
    
    all_selections = []
    # Dictionary untuk menghitung total peserta per kegiatan
    activity_counts_dict = {activity_name: 0 for activity_name in ACTIVITIES.keys()}

    for selection_entry in all_selections_raw:
        selection_dict = dict(selection_entry)
        try:
            selected_activities_list = json.loads(selection_dict['selected_activities'])
            selection_dict['selected_activities'] = selected_activities_list
            selection_dict['submission_date_wib'] = convert_utc_to_wib(selection_dict['submission_date'])
            all_selections.append(selection_dict)

            # Update hitungan per kegiatan
            for activity in selected_activities_list:
                if activity in activity_counts_dict:
                    activity_counts_dict[activity] += 1
        except json.JSONDecodeError:
            # Handle error if JSON is malformed
            pass
    
    # Konversi dictionary hitungan ke list of dicts untuk template
    activity_counts = [{'activity_type': name, 'total': count} for name, count in activity_counts_dict.items()]

    conn.close()
    return render_template('participants.html', all_selections=all_selections, activity_counts=activity_counts)


# Rute Halaman Dashboard Admin
@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        flash('Anda tidak memiliki izin untuk mengakses halaman admin.', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    # Mengambil semua pilihan final, join dengan tabel users untuk detail
    all_selections_raw = conn.execute('''
        SELECT ufs.id, u.name AS user_name, u.email, u.nim, u.jurusan, ufs.selected_activities, ufs.submission_date
        FROM user_final_selection ufs
        JOIN users u ON ufs.user_id = u.id
        ORDER BY ufs.submission_date DESC
    ''').fetchall()
    
    all_selections = []
    for selection_entry in all_selections_raw:
        selection_dict = dict(selection_entry)
        try:
            selection_dict['selected_activities'] = json.loads(selection_dict['selected_activities'])
            selection_dict['submission_date_wib'] = convert_utc_to_wib(selection_dict['submission_date'])
            all_selections.append(selection_dict)
        except json.JSONDecodeError:
            pass # Handle malformed JSON

    # Mengambil semua pengguna sistem
    all_users_raw = conn.execute('SELECT id, email, name, nim, jurusan, is_admin FROM users WHERE is_admin = 0 ORDER BY name ASC').fetchall()
    
    conn.close()
    
    return render_template('admin_dashboard.html', all_selections=all_selections, all_users=all_users_raw)


# Rute untuk Admin Menghapus Pilihan Kegiatan Pengguna
@app.route('/admin/delete_selection/<int:selection_id>', methods=['POST'])
def admin_delete_selection(selection_id):
    if not session.get('is_admin'):
        flash('Anda tidak memiliki izin untuk melakukan tindakan ini.', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    try:
        # Periksa apakah pilihan ada sebelum menghapus
        selection_to_delete = conn.execute('SELECT * FROM user_final_selection WHERE id = ?', (selection_id,)).fetchone()
        if selection_to_delete:
            conn.execute('DELETE FROM user_final_selection WHERE id = ?', (selection_id,))
            conn.commit()
            flash(f'Pilihan kegiatan ID {selection_id} berhasil dihapus.', 'success')
        else:
            flash('Pilihan kegiatan tidak ditemukan.', 'error')
    except Exception as e:
        flash(f'Terjadi kesalahan saat menghapus pilihan: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin_dashboard'))

# Rute untuk Admin Mengedit Pilihan Kegiatan Pengguna
@app.route('/admin/edit_selection/<int:selection_id>', methods=['GET', 'POST'])
def admin_edit_selection(selection_id):
    if not session.get('is_admin'):
        flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'error')
        return redirect(url_for('index'))

    conn = get_db_connection()
    selection_record = conn.execute('''
        SELECT ufs.id, ufs.user_id, ufs.selected_activities, ufs.submission_date,
               u.name AS user_name, u.email, u.nim, u.jurusan
        FROM user_final_selection ufs
        JOIN users u ON ufs.user_id = u.id
        WHERE ufs.id = ?
    ''', (selection_id,)).fetchone()

    if not selection_record:
        conn.close()
        flash('Pilihan kegiatan tidak ditemukan.', 'error')
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        new_selected_activities = request.form.getlist('selected_activities')
        # Admin juga bisa mengedit jurusan pengguna jika diperlukan
        new_jurusan = request.form.get('jurusan') 

        if not new_selected_activities or not (1 <= len(new_selected_activities) <= 3):
            flash('Anda harus memilih antara 1 hingga 3 kegiatan.', 'error')
            conn.close()
            # Render kembali halaman edit dengan pesan error dan data yang sama
            selection_record_dict = dict(selection_record)
            selection_record_dict['selected_activities'] = json.loads(selection_record_dict['selected_activities'])
            return render_template('admin_edit_selection.html', 
                                   selection=selection_record_dict, 
                                   activities_data=ACTIVITIES,
                                   all_jurusan=["Teknik Informatika", "Teknik Sipil", "Teknik Arsitektur", "Teknik Pertambangan"])

        try:
            # Update pilihan kegiatan di tabel user_final_selection
            json_activities = json.dumps(new_selected_activities)
            conn.execute('''
                UPDATE user_final_selection 
                SET selected_activities = ?, submission_date = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (json_activities, selection_id))

            # Update jurusan di tabel users (opsional, jika admin boleh mengedit)
            conn.execute('''
                UPDATE users
                SET jurusan = ?
                WHERE id = ?
            ''', (new_jurusan, selection_record['user_id']))

            conn.commit()
            flash(f'Pilihan kegiatan dan jurusan untuk {selection_record["user_name"]} berhasil diperbarui.', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            flash(f'Terjadi kesalahan saat memperbarui pilihan: {str(e)}', 'error')
            conn.close()
            # Render kembali halaman edit dengan pesan error dan data yang sama
            selection_record_dict = dict(selection_record)
            selection_record_dict['selected_activities'] = json.loads(selection_record_dict['selected_activities'])
            return render_template('admin_edit_selection.html', 
                                   selection=selection_record_dict, 
                                   activities_data=ACTIVITIES,
                                   all_jurusan=["Teknik Informatika", "Teknik Sipil", "Teknik Arsitektur", "Teknik Pertambangan"])
        finally:
            conn.close()
    
    # GET request
    selection_record_dict = dict(selection_record)
    selection_record_dict['selected_activities'] = json.loads(selection_record_dict['selected_activities'])
    
    conn.close()
    return render_template('admin_edit_selection.html', 
                           selection=selection_record_dict, 
                           activities_data=ACTIVITIES,
                           all_jurusan=["Teknik Informatika", "Teknik Sipil", "Teknik Arsitektur", "Teknik Pertambangan"])


if __name__ == '__main__':
    # Hapus database lama jika ada untuk memulai bersih (khusus development)
    # Anda bisa mengomentari ini untuk menjaga data jika ingin mempertahankan data
    if os.path.exists('kegiatan_registrasi.db'): 
        os.remove('kegiatan_registrasi.db') 
    
    init_db()
    
    conn = get_db_connection()
    # Buat pengguna admin default
    admin_user = conn.execute("SELECT * FROM users WHERE email = 'admin@example.com'").fetchone()
    if not admin_user:
        hashed_admin_password = generate_password_hash('adminjago')
        # Perubahan di sini: NIM dan Jurusan diatur menjadi None untuk akun admin
        conn.execute('INSERT INTO users (email, name, nim, jurusan, password_hash, is_admin) VALUES (?, ?, ?, ?, ?, ?)', 
                     ('admin@example.com', 'Administrator', None, None, hashed_admin_password, 1))
        conn.commit()
    conn.close()

    app.run(debug=True)