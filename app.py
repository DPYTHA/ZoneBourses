import os
import json
from flask import Flask, request, redirect, url_for, session, jsonify, render_template
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import psycopg2
from datetime import datetime, timedelta
import uuid

# Import depuis models.py corrigé
from models import (
    User, 
    save_uploaded_file, 
    allowed_file,
    save_multiple_files,
    parse_procedure_medias,
    create_debug_route
)

app = Flask(__name__)

# Configuration pour Railway
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'votre_cle_secrete_tres_securisee_zonebourse')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'mkv', 'pdf', 'doc', 'docx'}

# Configuration de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

class FlaskUser(UserMixin):
    """Classe User pour Flask-Login (version simplifiée)"""
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
    """Charge un utilisateur pour Flask-Login"""
    try:
        user = User.get_by_id(user_id)
        if user:
            # Convertir le User du models.py en FlaskUser pour Flask-Login
            return FlaskUser(
                user.id, user.nom, user.prenom, user.numero_whatsapp, 
                user.password, user.email, user.is_active, 
                user.is_admin, user.date_inscription
            )
        return None
    except Exception as e:
        print(f"Erreur dans load_user: {e}")
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

@app.route('/init-db-manual')
def init_db_manual():
    """Initialisation manuelle de la base de données - À APPELER UNE FOIS SUR RAILWAY"""
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'message': '❌ Impossible de se connecter à la DB'}), 500
        
        cur = conn.cursor()
        
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
        
        # Ajouter les colonnes manquantes si nécessaire
        try:
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='bourses' AND column_name='procedure_medias'")
            if not cur.fetchone():
                cur.execute('ALTER TABLE bourses ADD COLUMN procedure_medias TEXT')
                print("✅ Colonne procedure_medias ajoutée")
        except Exception as e:
            print(f"Note colonne procedure_medias: {e}")
        
        try:
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='bourses' AND column_name='is_active'")
            if not cur.fetchone():
                cur.execute('ALTER TABLE bourses ADD COLUMN is_active BOOLEAN DEFAULT TRUE')
                print("✅ Colonne is_active ajoutée")
        except Exception as e:
            print(f"Note colonne is_active: {e}")
        
        # Créer l'admin par défaut
        cur.execute('''
            INSERT INTO users (nom, prenom, numero_whatsapp, email, password, is_admin, is_active)
            VALUES ('Admin', 'System', '+2250710069791', 'moua18978@gmail.com', 'admin123', TRUE, TRUE)
            ON CONFLICT (numero_whatsapp) DO NOTHING
        ''')
        
        # Vérifier si des bourses existent déjà
        cur.execute('SELECT COUNT(*) FROM bourses')
        count = cur.fetchone()[0]
        
        if count == 0:
            # Insérer des bourses d'exemple avec des dates futures
            cur.execute('''
                INSERT INTO bourses (titre, description, pays, universite, niveau_etude, domaine_etude, montant_bourse, date_limite, conditions, procedure_postulation, is_active)
                VALUES 
                ('Bourse d''excellence en Informatique', 'Bourse complète pour étudier l''informatique en France avec tous les frais couverts.', 'France', 'Université Paris-Saclay', 'Master', 'Informatique', '15 000€ par an', '2025-06-30', 'Diplôme de licence en informatique, moyenne minimale de 14/20', '1. Remplir le formulaire en ligne\n2. Envoyer les documents requis\n3. Passer un entretien', TRUE),
                ('Bourse pour études en Génie Civil', 'Bourse partielle pour études de génie civil au Canada avec possibilité de stage.', 'Canada', 'Université de Montréal', 'Licence', 'Génie Civil', '10 000 CAD par an', '2025-07-15', 'Baccalauréat scientifique, bon niveau en mathématiques', '1. Créer un compte sur le portail de l''université\n2. Soumettre le dossier de candidature\n3. Attendre la réponse', TRUE),
                ('Bourse de Médecine aux USA', 'Bourse complète pour étudier la médecine aux États-Unis incluant les frais de scolarité et logement.', 'États-Unis', 'Harvard University', 'Doctorat', 'Médecine', '50 000$ par an', '2025-05-31', 'Diplôme de pré-médecine, excellents résultats académiques, TOEFL 100+', '1. Soumettre le dossier complet\n2. Passer un examen d''entrée\n3. Entretien avec le comité', TRUE)
            ''')
            print(f"✅ {cur.rowcount} bourses d'exemple insérées")
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': '✅ Base de données initialisée avec succès!',
            'admin_account': 'Numéro: +2250710069791 | Mot de passe: admin123'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'❌ Erreur: {str(e)}'}), 500

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

@app.route('/dashboard')
@login_required
def dashboard():
    """Tableau de bord utilisateur avec toutes les bourses"""
    try:
        conn = get_db_connection()
        if conn is None:
            return "Erreur de connexion à la base de données", 500
        
        cur = conn.cursor()
        
        # Récupérer toutes les bourses actives
        cur.execute('SELECT * FROM bourses WHERE is_active = TRUE ORDER BY date_limite ASC')
        bourses_data = cur.fetchall()
        
        # Récupérer les colonnes pour debug
        cur.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='bourses' ORDER BY ordinal_position
        """)
        columns = [col[0] for col in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        print(f"📊 {len(bourses_data)} bourses trouvées")
        print(f"📋 Colonnes bourses: {columns}")
        
        bourses = []
        for bourse in bourses_data:
            # Parser les médias de procédure
            procedure_medias = []
            if len(bourse) > 13 and bourse[13]:  # procedure_medias à l'index 13
                procedure_medias = parse_procedure_medias(bourse[13])
            
            # Créer l'objet bourse
            bourse_obj = {
                'id': bourse[0],
                'titre': bourse[1] if len(bourse) > 1 else 'Sans titre',
                'description': bourse[2] if len(bourse) > 2 else '',
                'pays': bourse[3] if len(bourse) > 3 else '',
                'universite': bourse[4] if len(bourse) > 4 else '',
                'niveau_etude': bourse[5] if len(bourse) > 5 else '',
                'domaine_etude': bourse[6] if len(bourse) > 6 else '',
                'montant_bourse': bourse[7] if len(bourse) > 7 else '',
                'date_limite': bourse[8].strftime('%d %B %Y') if len(bourse) > 8 and bourse[8] else '',
                'conditions': bourse[9] if len(bourse) > 9 else '',
                'procedure_postulation': bourse[10] if len(bourse) > 10 else '',
                'image_url': bourse[11] if len(bourse) > 11 else '',
                'video_url': bourse[12] if len(bourse) > 12 else '',
                'procedure_medias': procedure_medias,
                'has_media': bool(bourse[11] if len(bourse) > 11 else '' or bourse[12] if len(bourse) > 12 else ''),
                'has_procedure_medias': len(procedure_medias) > 0
            }
            bourses.append(bourse_obj)
        
        # Informations utilisateur
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
        print(f"❌ Erreur dans dashboard: {e}")
        return f"Erreur: {str(e)}", 500

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

@app.route('/renseignement')
def renseignement_page():
    return render_template('renseignement.html')

@app.route('/admin/users')
@login_required
def admin_users_page():
    """Page de gestion des utilisateurs"""
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    return render_template('admin_users.html')

# Routes API
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Données manquantes'}), 400
    
    numero_whatsapp = data.get('numero_whatsapp', '').strip()
    password = data.get('password', '').strip()
    
    if not numero_whatsapp or not password:
        return jsonify({'success': False, 'message': 'Numéro WhatsApp et mot de passe requis'}), 400
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': 'Erreur de connexion à la base de données'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute(
            'SELECT id, nom, prenom, numero_whatsapp, password, email, is_active, is_admin, date_inscription FROM users WHERE numero_whatsapp = %s', 
            (numero_whatsapp,)
        )
        user_data = cur.fetchone()
        cur.close()
        conn.close()
        
        if user_data and user_data[5] == password:  # Index 5 pour password
            user_obj = FlaskUser(*user_data)
            if user_obj.is_active:
                login_user(user_obj, remember=True)
                return jsonify({
                    'success': True,
                    'message': f'Bienvenue {user_obj.prenom} {user_obj.nom}!',
                    'user': {
                        'id': user_obj.id,
                        'nom': user_obj.nom,
                        'prenom': user_obj.prenom,
                        'is_admin': user_obj.is_admin
                    }
                })
            else:
                return jsonify({'success': False, 'message': 'Votre compte a été désactivé'}), 403
        else:
            return jsonify({'success': False, 'message': 'Numéro WhatsApp ou mot de passe incorrect'}), 401
    except Exception as e:
        print(f"Erreur login: {e}")
        return jsonify({'success': False, 'message': 'Erreur serveur'}), 500

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Données manquantes'}), 400
    
    nom = data.get('nom', '').strip()
    prenom = data.get('prenom', '').strip()
    numero_whatsapp = data.get('numero_whatsapp', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    confirm_password = data.get('confirm_password', '').strip()
    
    if not all([nom, prenom, numero_whatsapp, password, confirm_password]):
        return jsonify({'success': False, 'message': 'Tous les champs obligatoires doivent être remplis'}), 400
    
    if password != confirm_password:
        return jsonify({'success': False, 'message': 'Les mots de passe ne correspondent pas'}), 400
    
    # Vérifier si l'utilisateur existe déjà
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': 'Erreur de connexion à la base de données'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT id FROM users WHERE numero_whatsapp = %s', (numero_whatsapp,))
        existing_user = cur.fetchone()
        
        if existing_user:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Ce numéro WhatsApp est déjà utilisé'}), 409
        
        # Enregistrer l'utilisateur
        cur.execute(
            'INSERT INTO users (nom, prenom, numero_whatsapp, email, password, is_active) VALUES (%s, %s, %s, %s, %s, TRUE)',
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
        print(f"Erreur register: {e}")
        if conn:
            conn.rollback()
            cur.close()
            conn.close()
        return jsonify({'success': False, 'message': f'Erreur lors de l\'inscription: {str(e)}'}), 500

@app.route('/api/bourses')
@login_required
def api_bourses():
    """API pour récupérer toutes les bourses"""
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cur = conn.cursor()
        cur.execute('SELECT * FROM bourses WHERE is_active = TRUE ORDER BY date_limite ASC')
        bourses_data = cur.fetchall()
        cur.close()
        conn.close()
        
        bourses = []
        for bourse in bourses_data:
            procedure_medias = []
            if len(bourse) > 13 and bourse[13]:
                procedure_medias = parse_procedure_medias(bourse[13])
            
            bourses.append({
                'id': bourse[0],
                'titre': bourse[1] if len(bourse) > 1 else '',
                'description': bourse[2] if len(bourse) > 2 else '',
                'pays': bourse[3] if len(bourse) > 3 else '',
                'universite': bourse[4] if len(bourse) > 4 else '',
                'niveau_etude': bourse[5] if len(bourse) > 5 else '',
                'domaine_etude': bourse[6] if len(bourse) > 6 else '',
                'montant_bourse': bourse[7] if len(bourse) > 7 else '',
                'date_limite': bourse[8].strftime('%Y-%m-%d') if len(bourse) > 8 and bourse[8] else '',
                'conditions': bourse[9] if len(bourse) > 9 else '',
                'procedure_postulation': bourse[10] if len(bourse) > 10 else '',
                'image_url': bourse[11] if len(bourse) > 11 else '',
                'video_url': bourse[12] if len(bourse) > 12 else '',
                'procedure_medias': procedure_medias,
                'has_procedure_medias': len(procedure_medias) > 0
            })
        
        return jsonify(bourses)
    except Exception as e:
        print(f"Erreur api_bourses: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bourse/<int:bourse_id>')
@login_required
def api_bourse_detail(bourse_id):
    """API pour récupérer les détails d'une bourse spécifique"""
    try:
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
        
        procedure_medias = []
        if len(bourse_data) > 13 and bourse_data[13]:
            procedure_medias = parse_procedure_medias(bourse_data[13])
        
        bourse = {
            'id': bourse_data[0],
            'titre': bourse_data[1] if len(bourse_data) > 1 else '',
            'description': bourse_data[2] if len(bourse_data) > 2 else '',
            'pays': bourse_data[3] if len(bourse_data) > 3 else '',
            'universite': bourse_data[4] if len(bourse_data) > 4 else '',
            'niveau_etude': bourse_data[5] if len(bourse_data) > 5 else '',
            'domaine_etude': bourse_data[6] if len(bourse_data) > 6 else '',
            'montant_bourse': bourse_data[7] if len(bourse_data) > 7 else '',
            'date_limite': bourse_data[8].strftime('%d %B %Y') if len(bourse_data) > 8 and bourse_data[8] else '',
            'conditions': bourse_data[9] if len(bourse_data) > 9 else '',
            'procedure_postulation': bourse_data[10] if len(bourse_data) > 10 else '',
            'image_url': bourse_data[11] if len(bourse_data) > 11 else '',
            'video_url': bourse_data[12] if len(bourse_data) > 12 else '',
            'procedure_medias': procedure_medias,
            'has_procedure_medias': len(procedure_medias) > 0
        }
        
        return jsonify(bourse)
    except Exception as e:
        print(f"Erreur api_bourse_detail: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/users')
@login_required
def get_all_users():
    """Récupérer tous les utilisateurs (admin seulement)"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Accès non autorisé'}), 403
    
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
@login_required
def validate_user(user_id):
    """Valider un utilisateur - Ajouter 1 mois à la souscription"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Accès non autorisé'}), 403
    
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cur = conn.cursor()
        cur.execute('SELECT date_inscription FROM users WHERE id = %s', (user_id,))
        result = cur.fetchone()
        
        if not result:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Utilisateur non trouvé'})
        
        current_date = result[0] or datetime.now()
        new_date = current_date + timedelta(days=30)
        
        cur.execute('UPDATE users SET date_inscription = %s WHERE id = %s', (new_date, user_id))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Utilisateur validé - 1 mois ajouté'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    """Activer/Désactiver un utilisateur"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Accès non autorisé'}), 403
    
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cur = conn.cursor()
        cur.execute('UPDATE users SET is_active = NOT is_active WHERE id = %s', (user_id,))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Statut utilisateur modifié'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    """Supprimer un utilisateur"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Accès non autorisé'}), 403
    
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cur = conn.cursor()
        cur.execute('SELECT is_admin FROM users WHERE id = %s', (user_id,))
        result = cur.fetchone()
        
        if result and result[0]:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Impossible de supprimer un administrateur'})
        
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
    """Ajouter une nouvelle bourse (admin seulement)"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Accès non autorisé'}), 403
    
    try:
        # Récupérer les données de base
        titre = request.form.get('titre', '').strip()
        description = request.form.get('description', '').strip()
        pays = request.form.get('pays', '').strip()
        universite = request.form.get('universite', '').strip()
        niveau_etude = request.form.get('niveau_etude', '').strip()
        domaine_etude = request.form.get('domaine_etude', '').strip()
        montant_bourse = request.form.get('montant_bourse', '').strip()
        date_limite = request.form.get('date_limite', '').strip()
        conditions = request.form.get('conditions', '').strip()
        procedure_postulation = request.form.get('procedure_postulation', '').strip()
        
        # Validation des champs obligatoires
        if not all([titre, description, pays, universite, niveau_etude, domaine_etude, montant_bourse, date_limite]):
            return jsonify({'success': False, 'error': 'Tous les champs obligatoires doivent être remplis'}), 400
        
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
        if 'procedure_medias' in request.files:
            procedure_files = request.files.getlist('procedure_medias')
            procedure_medias = save_multiple_files(procedure_files)
        
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
            RETURNING id
        ''', (
            titre, description, pays, universite, niveau_etude, domaine_etude,
            montant_bourse, date_limite, conditions, procedure_postulation,
            image_url, video_url, procedure_medias_json
        ))
        
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': 'Bourse ajoutée avec succès',
            'bourse_id': new_id
        })
        
    except Exception as e:
        print(f"Erreur lors de l'ajout de la bourse: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logout')
@login_required
def api_logout():
    """Déconnexion"""
    logout_user()
    return jsonify({'success': True, 'message': 'Déconnexion réussie'})

# Routes de debug
@app.route('/debug/db-check')
def debug_db_check():
    """Vérifier l'état de la base de données"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'No DB connection'}), 500
        
        cur = conn.cursor()
        
        # Vérifier les tables
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = cur.fetchall()
        
        # Compter les bourses
        cur.execute("SELECT COUNT(*) FROM bourses")
        bourses_count = cur.fetchone()[0]
        
        # Vérifier les colonnes de bourses
        cur.execute("""
            SELECT column_name, data_type, ordinal_position
            FROM information_schema.columns
            WHERE table_name = 'bourses'
            ORDER BY ordinal_position
        """)
        columns = cur.fetchall()
        
        # Afficher quelques bourses
        cur.execute("SELECT id, titre, is_active FROM bourses ORDER BY id DESC LIMIT 5")
        sample_bourses = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'database_url': bool(os.environ.get('DATABASE_URL')),
            'tables': [t[0] for t in tables],
            'bourses_count': bourses_count,
            'bourses_columns': [
                {'position': col[2], 'name': col[0], 'type': col[1]} 
                for col in columns
            ],
            'sample_bourses': [
                {'id': b[0], 'titre': b[1], 'is_active': b[2]}
                for b in sample_bourses
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Ajouter les routes de debug depuis models.py
create_debug_route(app)

if __name__ == '__main__':
    # Créer le dossier uploads s'il n'existe pas
    os.makedirs('static/uploads', exist_ok=True)
    
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Application démarrée sur le port {port}")
    print(f"📁 Dossier upload: {app.config['UPLOAD_FOLDER']}")
    print(f"🔐 Secret key: {'Défini' if app.config['SECRET_KEY'] else 'Non défini'}")
    print(f"🌐 Railway DB: {'Oui' if os.environ.get('DATABASE_URL') else 'Non (mode local)'}")
    
    app.run(host='0.0.0.0', port=port, debug=False)