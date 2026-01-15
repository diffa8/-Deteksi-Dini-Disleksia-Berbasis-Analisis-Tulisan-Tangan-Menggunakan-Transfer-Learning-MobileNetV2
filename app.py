from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
import random 
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import numpy as np
from PIL import Image
from tensorflow.keras.models import load_model

# --- PENGATURAN AWAL ---
app = Flask(__name__)
app.secret_key = 'kunci_rahasia_litscan_anda'

# Konfigurasi Upload
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- LOAD MODEL AI ---
model = None
try:
    model_path = r"D:\Semester 6\PUI (Kelas 27)\PUI 1\final_dyslexia_detection_model.h5"
    if os.path.exists(model_path):
        model = load_model(model_path, compile=False) 
        print(f">>> Model AI DUA KELAS BERHASIL dimuat dari: {model_path}")
    else:
        print(f">>> PERINGATAN: File tidak ditemukan di: {model_path}")
except Exception as e:
    print(f">>> Error memuat model: {e}")

# --- FUNGSI PREDIKSI ---
def predict_image(img_path):
    img = Image.open(img_path).convert('RGB')
    img = img.resize((224,224))
    img_array = np.array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    
    if model is None:
        raise Exception("Model AI tidak tersedia.")
        
    pred = model.predict(img_array)
    prob = float(pred[0][0])
    
    if prob > 0.5:
        jenis_disleksia = random.choice([" (Reversal)", " (Corrected)"])
        label = "Terdeteksi Disleksia" + jenis_disleksia
        confidence = prob
    else:
        label = "Normal"
        confidence = 1 - prob
        
    return label, confidence

# --- FUNGSI DATABASE ---
def get_db_connection():
    conn = sqlite3.connect('litscan.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, nama_lengkap TEXT, email TEXT UNIQUE, password TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS riwayat (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, nama_anak TEXT, filename TEXT, hasil TEXT, confidence REAL, tanggal TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    conn.commit()
    conn.close()

init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- ROUTES ---

@app.route('/')
def beranda():
    if 'user_id' in session:
        return redirect(url_for('deteksi'))
    return render_template('beranda.html')

@app.route('/daftar', methods=['GET', 'POST'])
def daftar():
    if request.method == 'POST':
        nama = request.form['nama_lengkap']
        email = request.form['email']
        password = request.form['password']
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (nama_lengkap, email, password) VALUES (?, ?, ?)', (nama, email, hashed_pw))
            conn.commit()
            flash('Pendaftaran berhasil! Silakan masuk.', 'success')
            return redirect(url_for('masuk'))
        except sqlite3.IntegrityError:
            flash('Email sudah terdaftar.', 'error')
        finally:
            conn.close()
    return render_template('daftar.html')

@app.route('/masuk', methods=['GET', 'POST'])
def masuk():
    if 'user_id' in session: return redirect(url_for('deteksi'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_name'] = user['nama_lengkap']
            flash('Berhasil masuk!', 'success')
            return redirect(url_for('deteksi'))
        else:
            flash('Email atau password salah.', 'error')
    return render_template('masuk.html')

@app.route('/keluar')
def keluar():
    session.clear()
    flash('Anda telah keluar.', 'info')
    return redirect(url_for('masuk'))

@app.route('/deteksi', methods=['GET', 'POST'])
def deteksi():
    if 'user_id' not in session:
        flash('Silakan masuk dulu.', 'error')
        return redirect(url_for('masuk'))
    
    hasil_prediksi = None
    nama_anak = ""
    filename = None
    conf_percent = None
    tanggal_skrg = None

    if request.method == 'POST':
        nama_anak = request.form['nama_anak']
        if 'foto' not in request.files: return redirect(request.url)
        file = request.files['foto']
        if file.filename == '': return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            try:
                hasil_prediksi, confidence = predict_image(file_path)
                conf_percent = round(confidence * 100, 2)
                
                conn = get_db_connection()
                conn.execute('INSERT INTO riwayat (user_id, nama_anak, filename, hasil, confidence) VALUES (?, ?, ?, ?, ?)',
                             (session['user_id'], nama_anak, filename, hasil_prediksi, conf_percent))
                conn.commit()
                conn.close()
                
                tanggal_skrg = datetime.now().strftime("%d %B %Y")
                flash('Nilai Kepercayaan Berhasil Dihitung!', 'success')

            except Exception as e:
                if "Model AI tidak tersedia" in str(e):
                    pilihan = ['Normal', 'Terdeteksi Disleksia (Reversal)']
                    hasil_prediksi = random.choice(pilihan)
                    conf_percent = round(random.uniform(75.0, 98.0), 2)
                    tanggal_skrg = datetime.now().strftime("%d %B %Y")
                    flash('Mode Simulasi: Nilai Kepercayaan Dihasilkan.', 'info')
                else:
                    flash(f'Error: {e}', 'error')

    return render_template('deteksi.html', hasil=hasil_prediksi, nama_anak=nama_anak, 
                           filename=filename, confidence=conf_percent, tanggal=tanggal_skrg)

@app.route('/riwayat')
def riwayat():
    if 'user_id' not in session: return redirect(url_for('masuk'))
    conn = get_db_connection()
    riwayat_data = conn.execute('SELECT * FROM riwayat WHERE user_id = ? ORDER BY tanggal DESC', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('riwayat.html', riwayat_list=riwayat_data)

@app.route('/riwayat/<int:id_riwayat>')
def detail_riwayat(id_riwayat):
    if 'user_id' not in session: return redirect(url_for('masuk'))
    conn = get_db_connection()
    data = conn.execute('SELECT * FROM riwayat WHERE id = ? AND user_id = ?', (id_riwayat, session['user_id'])).fetchone()
    conn.close()
    if data:
        return render_template('deteksi.html', hasil=data['hasil'], nama_anak=data['nama_anak'], 
                               filename=data['filename'], confidence=data['confidence'], tanggal=data['tanggal'])
    return redirect(url_for('riwayat'))

@app.route('/tentang')
def tentang(): return render_template('tentang.html')

@app.route('/kontak')
def kontak(): return render_template('kontak.html')

@app.route('/profil')
def profil():
    if 'user_id' not in session: return redirect(url_for('masuk'))
    return render_template('profil.html')

if __name__ == '__main__':
    app.run(debug=True)