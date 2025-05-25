from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt 
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'gizli_anahtarınız'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///banka.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

class Kullanici(db.Model):
    __tablename__ = 'kullanici'
    id = db.Column(db.Integer, primary_key=True)
    isim = db.Column(db.String(100), unique=True, nullable=False)
    sifre_hash = db.Column(db.String(128), nullable=False)
    bakiye = db.Column(db.Float, default=0.0)
    hareketler = db.relationship('Hareket', backref='kullanici', lazy=True)

    def check_password(self, sifre):
        return bcrypt.check_password_hash(self.sifre_hash, sifre)

class Hareket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanici.id'), nullable=False)
    islem_turu = db.Column(db.String(10))
    miktar = db.Column(db.Float)
    tarih = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        isim = request.form['isim']
        sifre = request.form['sifre']
        if Kullanici.query.filter_by(isim=isim).first():
            flash('Bu kullanıcı adı zaten alınmış.', 'error')
        else:
            hashli = bcrypt.generate_password_hash(sifre).decode('utf-8')
            yeni = Kullanici(isim=isim, sifre_hash=hashli)
            db.session.add(yeni)
            db.session.commit()
            flash('Kayıt başarılı, lütfen giriş yapın.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        isim = request.form['isim']
        sifre = request.form['sifre']
        user = Kullanici.query.filter_by(isim=isim).first()
        if user and user.check_password(sifre):
            session['user_id'] = user.id
            flash('Giriş başarılı!', 'success')
            return redirect(url_for('hesap'))
        else:
            flash('Kullanıcı adı veya şifre hatalı.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Başarıyla çıkış yapıldı.', 'info')
    return redirect(url_for('index'))

@app.route('/hesap', methods=['GET', 'POST'])
def hesap():
    if 'user_id' not in session:
        flash('Lütfen önce giriş yapın.', 'error')
        return redirect(url_for('login'))

    kullanici = Kullanici.query.get(session['user_id'])

    if request.method == 'POST':
        islem = request.form['islem']
        miktar = float(request.form['miktar'])

        if islem == 'yatir' and miktar > 0:
            kullanici.bakiye += miktar
            hareket = Hareket(kullanici_id=kullanici.id, islem_turu='Yatırma', miktar=miktar)
            db.session.add(hareket)

        elif islem == 'cek' and 0 < miktar <= kullanici.bakiye:
            kullanici.bakiye -= miktar
            hareket = Hareket(kullanici_id=kullanici.id, islem_turu='Çekme', miktar=miktar)
            db.session.add(hareket)

        else:
            flash('İşlem hatası: geçersiz miktar veya yetersiz bakiye.', 'error')
            return redirect(url_for('hesap'))

        db.session.commit()
        flash('İşlem başarılı.', 'success')
        return redirect(url_for('hesap'))

    hareketler = Hareket.query.filter_by(kullanici_id=kullanici.id).order_by(Hareket.tarih.desc()).all()
    return render_template('bakiye.html', kullanici=kullanici, hareketler=hareketler)


@app.route('/islem_gecmisi')
def islem_gecmisi():
    if 'user_id' not in session:
        flash('Lütfen önce giriş yapın.', 'error')
        return redirect(url_for('login'))

    kullanici = Kullanici.query.get(session['user_id'])
    hareketler = Hareket.query.filter_by(kullanici_id=kullanici.id).order_by(Hareket.tarih.desc()).all()
    return render_template('gecmis.html', kullanici=kullanici, hareketler=hareketler)

if __name__ == '__main__':
    app.run(debug=True)
