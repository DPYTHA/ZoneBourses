import os
import json
from flask import Flask, request, redirect, url_for, session, jsonify, render_template
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import psycopg2
from urllib.parse import urlparse
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)

# Configuration pour Railway
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'votre_cle_secrete_tres_securisee_zonebourse')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

# Configuration de la base de données pour Railway
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # Pour Railway (URL de connexion PostgreSQL)
    url = urlparse(DATABASE_URL)
    DB_CONFIG = {
        'dbname': url.path[1:],
        'user': url.username,
        'password': url.password,
        'host': url.hostname,
        'port': url.port
    }
    print(f"✅ Configuration DB Railway détectée: {url.hostname}")
else:
    # Pour le développement local
    DB_CONFIG = {
        'dbname': 'Minizone_db',
        'user': 'Zone_user',
        'password': 'Pytha1991',
        'host': 'localhost',
        'port': '5432'
    }
    print("⚠️  Configuration DB locale")

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'mkv'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file):
    if file and file.filename and file.filename != '':
        if allowed_file(file.filename):
            # Créer le dossier s'il n'existe pas
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            # Générer un nom de fichier unique
            file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            filename = f"{uuid.uuid4().hex}.{file_ext}" if file_ext else f"{uuid.uuid4().hex}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            try:
                file.save(filepath)
                print(f"✅ Fichier sauvegardé: {filename} -> {filepath}")
                return f"/static/uploads/{filename}"
            except Exception as e:
                print(f"❌ Erreur sauvegarde fichier: {e}")
                return None
        else:
            print(f"❌ Format non autorisé: {file.filename}")
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
    
    cur = conn.cursor()
    cur.execute('SELECT id, nom, prenom, numero_whatsapp, password, email, is_active, is_admin, date_inscription FROM users WHERE id = %s', (user_id,))
    user_data = cur.fetchone()
    cur.close()
    conn.close()
    
    if user_data:
        return User(*user_data)
    return None

def get_db_connection():
    """Établit une connexion à la base de données"""
    try:
        # Utilisez DATABASE_URL pour Railway, sinon la config locale
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if DATABASE_URL:
            # Pour Railway avec SSL
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            print("✅ Connexion à la DB Railway établie")
        else:
            # Pour le développement local
            conn = psycopg2.connect(**DB_CONFIG)
            print("✅ Connexion à la DB locale établie")
        return conn
    except Exception as e:
        print(f"❌ Erreur de connexion à la base de données: {e}")
        return None

def init_db():
    """Initialise la base de données avec les tables nécessaires"""
    conn = get_db_connection()
    if conn is None:
        print("⚠️  Impossible de se connecter à la base de données, skip init_db")
        return
    
    cur = conn.cursor()
    
    try:
        # Création de la table utilisateurs
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
        
        # Création de la table des bourses
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
        
        # Ajouter la colonne procedure_medias si elle n'existe pas
        try:
            cur.execute('''
                ALTER TABLE bourses 
                ADD COLUMN IF NOT EXISTS procedure_medias TEXT
            ''')
        except Exception as e:
            print(f"Note: {e}")
        
        # Ajouter la colonne is_active si elle n'existe pas
        try:
            cur.execute('ALTER TABLE bourses ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE')
        except Exception as e:
            print(f"Note: {e}")
        
        # Créer l'admin par défaut
        cur.execute('''
            INSERT INTO users (nom, prenom, numero_whatsapp, email, password, is_admin, is_active)
            VALUES ('Admin', 'System', '+2250710069791', 'moua18978@gmail.com', 'admin123', TRUE, TRUE)
            ON CONFLICT (numero_whatsapp) DO NOTHING
        ''')
        
        # Insérer des bourses d'exemple
        cur.execute('''
            INSERT INTO bourses (titre, description, pays, universite, niveau_etude, domaine_etude, montant_bourse, date_limite, conditions, procedure_postulation, is_active)
            VALUES 
            ('Bourse d''excellence en Informatique', 'Bourse complète pour étudier l''informatique en France avec tous les frais couverts.', 'France', 'Université Paris-Saclay', 'Master', 'Informatique', '15 000€ par an', '2024-06-30', 'Diplôme de licence en informatique, moyenne minimale de 14/20', '1. Remplir le formulaire en ligne\n2. Envoyer les documents requis\n3. Passer un entretien', TRUE),
            ('Bourse pour études en Génie Civil', 'Bourse partielle pour études de génie civil au Canada avec possibilité de stage.', 'Canada', 'Université de Montréal', 'Licence', 'Génie Civil', '10 000 CAD par an', '2024-07-15', 'Baccalauréat scientifique, bon niveau en mathématiques', '1. Créer un compte sur le portail de l''université\n2. Soumettre le dossier de candidature\n3. Attendre la réponse', TRUE)
            ON CONFLICT DO NOTHING
        ''')
        
        conn.commit()
        print("✅ Base de données initialisée avec succès")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation de la base: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

# Routes principales
@app.route('/')
def splash():
    return render_template('splash.html')

@app.route('/home')
def home():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/api/init-db')
def init_database():
    """Route pour initialiser la base de données manuellement"""
    try:
        init_db()
        return jsonify({'success': True, 'message': 'Base de données initialisée'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/dashboard')
@login_required
def dashboard():
    # Récupérer les bourses depuis la base de données
    conn = get_db_connection()
    if conn is None:
        return "Erreur de connexion à la base de données", 500
    
    cur = conn.cursor()
    
    try:
        cur.execute('SELECT * FROM bourses WHERE is_active = TRUE')
    except Exception as e:
        cur.execute('SELECT * FROM bourses')
    
    bourses_data = cur.fetchall()
    cur.close()
    conn.close()
    
    bourses = []
    for bourse in bourses_data:
        # Parser les médias de procédure
        procedure_medias = []
        if bourse[13]:  # procedure_medias est à l'index 13
            try:
                if isinstance(bourse[13], str):
                    procedure_medias = json.loads(bourse[13])
                elif isinstance(bourse[13], list):
                    procedure_medias = bourse[13]
            except json.JSONDecodeError:
                procedure_medias = []
        
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
    
    # Passer les informations utilisateur au template
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

@app.route('/bourse/<int:bourse_id>')
@login_required
def bourse_detail_page(bourse_id):
    return render_template('bourse_detail.html', bourse_id=bourse_id)

@app.route('/admin')
@login_required
def admin_page():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    return render_template('admin.html')

# Route pour ajouter une bourse
@app.route('/api/bourses', methods=['POST'])
@login_required
def api_add_bourse():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Accès non autorisé'}), 403
    
    try:
        # Récupérer les données du formulaire
        titre = request.form.get('titre')
        description = request.form.get('description')
        pays = request.form.get('pays')
        universite = request.form.get('universite')
        niveau_etude = request.form.get('niveau_etude')
        domaine_etude = request.form.get('domaine_etude')
        montant_bourse = request.form.get('montant_bourse')
        date_limite = request.form.get('date_limite')
        conditions = request.form.get('conditions')
        procedure_postulation = request.form.get('procedure_postulation')
        
        # Validation des champs obligatoires
        if not all([titre, description, pays, universite, niveau_etude, domaine_etude, montant_bourse, date_limite]):
            return jsonify({'success': False, 'message': 'Tous les champs obligatoires doivent être remplis'}), 400
        
        # Gérer l'upload de l'image principale
        image_url = None
        if 'image_url' in request.files:
            image_file = request.files['image_url']
            if image_file and image_file.filename:
                image_url = save_uploaded_file(image_file)
        
        # Gérer l'upload de la vidéo
        video_url = None
        if 'video_url' in request.files:
            video_file = request.files['video_url']
            if video_file and video_file.filename:
                video_url = save_uploaded_file(video_file)
        
        # Gérer les médias supplémentaires pour la procédure
        procedure_medias = []
        if 'procedure_medias' in request.files:
            for file in request.files.getlist('procedure_medias'):
                if file and file.filename and file.filename != '':
                    media_url = save_uploaded_file(file)
                    if media_url:
                        procedure_medias.append(media_url)
        
        # Convertir la liste en JSON pour la base de données
        procedure_medias_json = json.dumps(procedure_medias) if procedure_medias else '[]'
        
        # Insérer dans la base de données
        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'message': 'Erreur de connexion à la base de données'}), 500
        
        cur = conn.cursor()
        
        cur.execute('''
            INSERT INTO bourses 
            (titre, description, pays, universite, niveau_etude, domaine_etude, 
             montant_bourse, date_limite, conditions, procedure_postulation, 
             image_url, video_url, procedure_medias)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (titre, description, pays, universite, niveau_etude, domaine_etude,
              montant_bourse, date_limite, conditions, procedure_postulation,
              image_url, video_url, procedure_medias_json))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': 'Bourse ajoutée avec succès!'
        })
        
    except Exception as e:
        print(f"Erreur lors de l'ajout de la bourse: {e}")
        return jsonify({'success': False, 'message': f'Erreur lors de l\'ajout de la bourse: {str(e)}'}), 500

# Routes API
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Données manquantes'}), 400
    
    numero_whatsapp = data.get('numero_whatsapp')
    password = data.get('password')
    
    if not numero_whatsapp or not password:
        return jsonify({'success': False, 'message': 'Numéro WhatsApp et mot de passe requis'}), 400
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': 'Erreur de connexion à la base de données'}), 500
    
    cur = conn.cursor()
    cur.execute('SELECT id, nom, prenom, numero_whatsapp, password, email, is_active, is_admin, date_inscription FROM users WHERE numero_whatsapp = %s', (numero_whatsapp,))
    user_data = cur.fetchone()
    cur.close()
    conn.close()
    
    if user_data and user_data[4] == password:
        user = User(*user_data)
        if user.is_active:
            login_user(user)
            return jsonify({
                'success': True,
                'message': f'Bienvenue {user.prenom} {user.nom}!',
                'user': {
                    'id': user.id,
                    'nom': user.nom,
                    'prenom': user.prenom,
                    'is_admin': user.is_admin
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Votre compte a été désactivé'}), 403
    else:
        return jsonify({'success': False, 'message': 'Numéro WhatsApp ou mot de passe incorrect'}), 401

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Données manquantes'}), 400
    
    nom = data.get('nom')
    prenom = data.get('prenom')
    numero_whatsapp = data.get('numero_whatsapp')
    email = data.get('email', '')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    
    if not all([nom, prenom, numero_whatsapp, password, confirm_password]):
        return jsonify({'success': False, 'message': 'Tous les champs obligatoires doivent être remplis'}), 400
    
    if password != confirm_password:
        return jsonify({'success': False, 'message': 'Les mots de passe ne correspondent pas'}), 400
    
    # Vérifier si l'utilisateur existe déjà
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': 'Erreur de connexion à la base de données'}), 500
    
    cur = conn.cursor()
    cur.execute('SELECT id FROM users WHERE numero_whatsapp = %s', (numero_whatsapp,))
    existing_user = cur.fetchone()
    
    if existing_user:
        cur.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Ce numéro WhatsApp est déjà utilisé'}), 409
    
    # Enregistrer l'utilisateur
    try:
        cur.execute(
            'INSERT INTO users (nom, prenom, numero_whatsapp, email, password) VALUES (%s, %s, %s, %s, %s)',
            (nom, prenom, numero_whatsapp, email, password)
        )
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Inscription réussie! Vous pouvez maintenant vous connecter.'
        })
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Erreur lors de l\'inscription'}), 500

@app.route('/api/bourses')
@login_required
def api_bourses():
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cur = conn.cursor()
    
    try:
        cur.execute('SELECT * FROM bourses WHERE is_active = TRUE')
    except Exception as e:
        cur.execute('SELECT * FROM bourses')
    
    bourses_data = cur.fetchall()
    cur.close()
    conn.close()
    
    bourses = []
    for bourse in bourses_data:
        # Parser les médias de procédure
        procedure_medias = []
        if bourse[13]:
            try:
                if isinstance(bourse[13], str):
                    procedure_medias = json.loads(bourse[13])
                elif isinstance(bourse[13], list):
                    procedure_medias = bourse[13]
            except json.JSONDecodeError:
                procedure_medias = []
        
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
    
    return jsonify(bourses)

@app.route('/api/bourse/<int:bourse_id>')
@login_required
def api_bourse_detail(bourse_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cur = conn.cursor()
    cur.execute('SELECT * FROM bourses WHERE id = %s', (bourse_id,))
    bourse_data = cur.fetchone()
    cur.close()
    conn.close()
    
    if not bourse_data:
        return jsonify({'error': 'Bourse non trouvée'}), 404
    
    # Parser les médias de procédure
    procedure_medias = []
    if bourse_data[13]:  # Index 13 pour procedure_medias
        try:
            if isinstance(bourse_data[13], str) and bourse_data[13].strip():
                procedure_medias = json.loads(bourse_data[13])
            elif isinstance(bourse_data[13], (list, dict)):
                procedure_medias = bourse_data[13]
        except json.JSONDecodeError as e:
            procedure_medias = []
        except Exception as e:
            procedure_medias = []
    
    bourse = {
        'id': bourse_data[0],
        'titre': bourse_data[1],
        'description': bourse_data[2],
        'pays': bourse_data[3],
        'universite': bourse_data[4],
        'niveau_etude': bourse_data[5],
        'domaine_etude': bourse_data[6],
        'montant_bourse': bourse_data[7],
        'date_limite': bourse_data[8].strftime('%d %B %Y') if bourse_data[8] else '',
        'conditions': bourse_data[9],
        'procedure_postulation': bourse_data[10],
        'image_url': bourse_data[11],
        'video_url': bourse_data[12],
        'procedure_medias': procedure_medias,
        'has_procedure_medias': len(procedure_medias) > 0
    }
    
    return jsonify(bourse)

@app.route('/renseignement')
def renseignement_page():
    return render_template('renseignement.html')

# Gestion des utilisateurs
@app.route('/admin/users')
def admin_users_page():
    """Page de gestion des utilisateurs"""
    return render_template('admin_users.html')

@app.route('/api/admin/users')
def get_all_users():
    """Récupérer tous les utilisateurs"""
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cur = conn.cursor()
        cur.execute('''
            SELECT id, nom, prenom, numero_whatsapp, password, email, 
                   is_active, is_admin, date_inscription 
            FROM users 
            ORDER BY date_inscription DESC
        ''')
        users = cur.fetchall()
        cur.close()
        conn.close()
        
        users_list = []
        for user in users:
            users_list.append({
                'id': user[0],
                'nom': user[1],
                'prenom': user[2],
                'numero_whatsapp': user[3],
                'password': user[4],
                'email': user[5],
                'is_active': user[6],
                'is_admin': user[7],
                'date_inscription': user[8].isoformat() if user[8] else None
            })
        
        return jsonify({'success': True, 'users': users_list})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/users/<int:user_id>/validate', methods=['POST'])
def validate_user(user_id):
    """Valider un utilisateur - Ajouter 1 mois à la souscription"""
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cur = conn.cursor()
        
        # Récupérer la date actuelle d'inscription
        cur.execute('SELECT date_inscription FROM users WHERE id = %s', (user_id,))
        result = cur.fetchone()
        
        if not result:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Utilisateur non trouvé'})
        
        current_date = result[0]
        new_date = current_date + timedelta(days=30)  # Ajouter 1 mois
        
        # Mettre à jour la date
        cur.execute('UPDATE users SET date_inscription = %s WHERE id = %s', (new_date, user_id))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Utilisateur validé - 1 mois ajouté'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/users/<int:user_id>/toggle-status', methods=['POST'])
def toggle_user_status(user_id):
    """Activer/Désactiver un utilisateur"""
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cur = conn.cursor()
        
        # Inverser le statut is_active
        cur.execute('UPDATE users SET is_active = NOT is_active WHERE id = %s', (user_id,))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Statut utilisateur modifié'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Supprimer un utilisateur"""
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cur = conn.cursor()
        
        # Vérifier que l'utilisateur n'est pas admin
        cur.execute('SELECT is_admin FROM users WHERE id = %s', (user_id,))
        result = cur.fetchone()
        
        if result and result[0]:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Impossible de supprimer un administrateur'})
        
        # Supprimer l'utilisateur
        cur.execute('DELETE FROM users WHERE id = %s', (user_id,))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Utilisateur supprimé'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/bourses', methods=['POST'])
@login_required
def add_bourse():
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Accès non autorisé'}), 403
    
    try:
        # Récupérer les données de base
        titre = request.form.get('titre')
        description = request.form.get('description')
        pays = request.form.get('pays')
        universite = request.form.get('universite')
        niveau_etude = request.form.get('niveau_etude')
        domaine_etude = request.form.get('domaine_etude')
        montant_bourse = request.form.get('montant_bourse')
        date_limite = request.form.get('date_limite')
        conditions = request.form.get('conditions')
        procedure_postulation = request.form.get('procedure_postulation')
        
        # Gérer l'image principale
        image_url = None
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and image_file.filename != '':
                image_url = save_uploaded_file(image_file)
        
        # Gérer la vidéo principale
        video_url = None
        if 'video' in request.files:
            video_file = request.files['video']
            if video_file and video_file.filename != '':
                video_url = save_uploaded_file(video_file)
        
        # Gérer les médias de procédure
        procedure_medias = []
        
        # Via le champ multiple
        if 'procedure_medias' in request.files:
            procedure_files = request.files.getlist('procedure_medias')
            
            for media_file in procedure_files:
                if media_file and media_file.filename != '':
                    media_url = save_uploaded_file(media_file)
                    if media_url:
                        filename_lower = media_file.filename.lower()
                        is_video = filename_lower.endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm'))
                        is_image = filename_lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'))
                        
                        media_type = 'video' if is_video else 'image' if is_image else 'file'
                        
                        procedure_medias.append({
                            'url': media_url,
                            'type': media_type,
                            'filename': media_file.filename
                        })
        
        # Connexion à la base de données
        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'error': 'Erreur de connexion à la base de données'}), 500
        
        cur = conn.cursor()
        
        # Préparer la valeur procedure_medias
        procedure_medias_json = json.dumps(procedure_medias) if procedure_medias else None
        
        # Insérer la bourse
        cur.execute('''
            INSERT INTO bourses 
            (titre, description, pays, universite, niveau_etude, domaine_etude, 
             montant_bourse, date_limite, conditions, procedure_postulation, 
             image_url, video_url, procedure_medias, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
        ''', (
            titre, description, pays, universite, niveau_etude, domaine_etude,
            montant_bourse, date_limite, conditions, procedure_postulation,
            image_url, video_url, procedure_medias_json
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Bourse ajoutée avec succès'})
        
    except Exception as e:
        print(f"Erreur lors de l'ajout de la bourse: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logout')
@login_required
def api_logout():
    logout_user()
    return jsonify({'success': True, 'message': 'Déconnexion réussie'})

if __name__ == '__main__':
    # N'appelez pas init_db() automatiquement au démarrage
    # Laissez Railway gérer la base de données
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)