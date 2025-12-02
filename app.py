# REMPLACEZ TOUTE LA SECTION DATABASE CONFIGURATION PAR CE CODE :

import os
import json
from flask import Flask, request, redirect, url_for, session, jsonify, render_template
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import psycopg2
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)

# Configuration pour Railway
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'votre_cle_secrete_tres_securisee_zonebourse')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'mkv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file):
    if file and file.filename and file.filename != '':
        if allowed_file(file.filename):
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            filename = f"{uuid.uuid4().hex}.{file_ext}" if file_ext else f"{uuid.uuid4().hex}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            try:
                file.save(filepath)
                return f"/static/uploads/{filename}"
            except Exception as e:
                print(f"❌ Erreur sauvegarde fichier: {e}")
                return None
    return None

# Configuration de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

class User(UserMixin):
    def __init__(self, id, nom, prenom, numero_whatsapp, password, email, is_active, is_admin, date_inscription):
        self.id = id
        self.nom = nom
        self.prenom = prenom
        self.numero_whatsapp = numero_whatsapp
        self.password = password
        self.email = email
        self._is_active = is_active
        self.is_admin = is_admin
        self.date_inscription = date_inscription

    @property
    def is_active(self):
        return self._is_active

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    if conn is None:
        return None
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT id, nom, prenom, numero_whatsapp, password, email, is_active, is_admin, date_inscription FROM users WHERE id = %s', (user_id,))
        user_data = cur.fetchone()
        cur.close()
        conn.close()
        
        if user_data:
            return User(*user_data)
        return None
    except Exception as e:
        print(f"Erreur load_user: {e}")
        return None

def get_db_connection():
    """Établit une connexion à la base de données"""
    try:
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if DATABASE_URL:
            # Pour Railway avec SSL
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            print("✅ Connexion à la DB Railway établie")
        else:
            # Pour le développement local
            conn = psycopg2.connect(
                dbname='Minizone_db',
                user='Zone_user',
                password='Pytha1991',
                host='localhost',
                port='5432'
            )
            print("✅ Connexion à la DB locale établie")
        return conn
    except Exception as e:
        print(f"❌ Erreur de connexion à la base de données: {e}")
        return None

# IMPORTANT: Ajoutez cette route pour initialiser la base
@app.route('/init-db-manual')
def init_db_manual():
    """Initialisation manuelle de la base"""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Impossible de se connecter à la DB", 500
        
        cur = conn.cursor()
        
        # Créer table users
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                nom VARCHAR(100) NOT NULL,
                prenom VARCHAR(100) NOT NULL,
                numero_whatsapp VARCHAR(20) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                is_admin BOOLEAN DEFAULT FALSE,
                date_inscription TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Créer table bourses
        cur.execute('''
            CREATE TABLE IF NOT EXISTS bourses (
                id SERIAL PRIMARY KEY,
                titre VARCHAR(255) NOT NULL,
                description TEXT,
                pays VARCHAR(100),
                universite VARCHAR(255),
                niveau_etude VARCHAR(100),
                domaine_etude VARCHAR(255),
                montant_bourse VARCHAR(100),
                date_limite DATE,
                conditions TEXT,
                procedure_postulation TEXT,
                image_url VARCHAR(500),
                video_url VARCHAR(500),
                procedure_medias TEXT,
                date_publication TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # Vérifier et ajouter colonnes manquantes
        try:
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='bourses' AND column_name='procedure_medias'")
            if not cur.fetchone():
                cur.execute('ALTER TABLE bourses ADD COLUMN procedure_medias TEXT')
        except:
            pass
        
        try:
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='bourses' AND column_name='is_active'")
            if not cur.fetchone():
                cur.execute('ALTER TABLE bourses ADD COLUMN is_active BOOLEAN DEFAULT TRUE')
        except:
            pass
        
        # Insérer admin par défaut
        cur.execute('''
            INSERT INTO users (nom, prenom, numero_whatsapp, email, password, is_admin, is_active)
            VALUES ('Admin', 'System', '+2250710069791', 'moua18978@gmail.com', 'admin123', TRUE, TRUE)
            ON CONFLICT (numero_whatsapp) DO NOTHING
        ''')
        
        # Vérifier si des bourses existent déjà
        cur.execute('SELECT COUNT(*) FROM bourses')
        count = cur.fetchone()[0]
        
        if count == 0:
            # Insérer des bourses d'exemple
            cur.execute('''
                INSERT INTO bourses (titre, description, pays, universite, niveau_etude, domaine_etude, montant_bourse, date_limite, conditions, procedure_postulation, is_active)
                VALUES 
                ('Bourse d''excellence en Informatique', 'Bourse complète pour étudier l''informatique en France avec tous les frais couverts.', 'France', 'Université Paris-Saclay', 'Master', 'Informatique', '15 000€ par an', '2025-06-30', 'Diplôme de licence en informatique, moyenne minimale de 14/20', '1. Remplir le formulaire en ligne\n2. Envoyer les documents requis\n3. Passer un entretien', TRUE),
                ('Bourse pour études en Génie Civil', 'Bourse partielle pour études de génie civil au Canada avec possibilité de stage.', 'Canada', 'Université de Montréal', 'Licence', 'Génie Civil', '10 000 CAD par an', '2025-07-15', 'Baccalauréat scientifique, bon niveau en mathématiques', '1. Créer un compte sur le portail de l''université\n2. Soumettre le dossier de candidature\n3. Attendre la réponse', TRUE)
            ''')
        
        conn.commit()
        cur.close()
        conn.close()
        
        return "✅ Base de données initialisée avec succès!"
        
    except Exception as e:
        return f"❌ Erreur: {str(e)}", 500

# Routes principales (gardez vos routes existantes)
@app.route('/')
def splash():
    return render_template('splash.html')

@app.route('/home')
def home():
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    if conn is None:
        return "Erreur de connexion à la base de données", 500
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM bourses WHERE is_active = TRUE ORDER BY id DESC')
        bourses_data = cur.fetchall()
        cur.close()
        conn.close()
        
        bourses = []
        for bourse in bourses_data:
            procedure_medias = []
            if bourse[13]:  # procedure_medias
                try:
                    if isinstance(bourse[13], str):
                        procedure_medias = json.loads(bourse[13])
                except:
                    pass
            
            bourses.append({
                'id': bourse[0],
                'titre': bourse[1],
                'description': bourse[2],
                'pays': bourse[3],
                'universite': bourse[4],
                'niveau_etude': bourse[5],
                'domaine_etude': bourse[6],
                'montant_bourse': bourse[7],
                'date_limite': bourse[8].strftime('%d %B %Y') if bourse[8] else '',
                'conditions': bourse[9],
                'procedure_postulation': bourse[10],
                'image_url': bourse[11],
                'video_url': bourse[12],
                'procedure_medias': procedure_medias
            })
        
        user_info = {
            'id': current_user.id,
            'nom': current_user.nom,
            'prenom': current_user.prenom,
            'email': current_user.email,
            'numero_whatsapp': current_user.numero_whatsapp,
            'is_admin': current_user.is_admin,
            'date_inscription': current_user.date_inscription.strftime('%d/%m/%Y') if current_user.date_inscription else ''
        }
        
        return render_template('dashboard.html', user=current_user, bourses=bourses, user_info=user_info)
        
    except Exception as e:
        return f"Erreur: {str(e)}", 500

# ... (gardez vos autres routes existantes)

# Route de debug
@app.route('/debug/db-structure')
def debug_db_structure():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'No connection'}), 500
    
    cur = conn.cursor()
    
    # Vérifier tables
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    tables = cur.fetchall()
    
    # Compter bourses
    cur.execute("SELECT COUNT(*) FROM bourses")
    bourses_count = cur.fetchone()[0]
    
    # Afficher quelques bourses
    cur.execute("SELECT id, titre FROM bourses ORDER BY id DESC LIMIT 5")
    sample_bourses = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return jsonify({
        'tables': [t[0] for t in tables],
        'bourses_count': bourses_count,
        'sample_bourses': [{'id': b[0], 'titre': b[1]} for b in sample_bourses],
        'railway_db': bool(os.environ.get('DATABASE_URL'))
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)