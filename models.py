from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    deteksis = db.relationship('Deteksi', backref='user', lazy=True)

class Deteksi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_anak = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    gambar = db.Column(db.String(200), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)