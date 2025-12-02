import os
import psycopg2
from datetime import datetime
from flask_login import UserMixin
import uuid
from urllib.parse import urlparse

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'mkv'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file):
    if file and allowed_file(file.filename):
        # Créer le dossier s'il n'existe pas
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Générer un nom de fichier unique
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{file_ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        file.save(filepath)
        return f"/static/uploads/{filename}"
    return None

# Configuration de la base de données pour Railway
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """Établit une connexion à la base de données"""
    try:
        # Utilisez DATABASE_URL pour Railway, sinon la config locale
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

    @staticmethod
    def get(user_id):
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

    @staticmethod
    def get_by_whatsapp(numero_whatsapp):
        conn = get_db_connection()
        if conn is None:
            return None
        
        cur = conn.cursor()
        cur.execute('SELECT id, nom, prenom, numero_whatsapp, password, email, is_active, is_admin, date_inscription FROM users WHERE numero_whatsapp = %s', (numero_whatsapp,))
        user_data = cur.fetchone()
        cur.close()
        conn.close()
        
        if user_data:
            return User(*user_data)
        return None

# Route de debug pour vérifier la structure de la base
from flask import jsonify

def create_debug_route(app):
    @app.route('/debug/check-db')
    def debug_check_db():
        """Route de debug pour vérifier la structure de la base"""
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'DB connection failed'}), 500
        
        cur = conn.cursor()
        
        # Structure de la table bourses
        cur.execute("""
            SELECT column_name, data_type, ordinal_position
            FROM information_schema.columns
            WHERE table_name = 'bourses'
            ORDER BY ordinal_position
        """)
        
        columns = cur.fetchall()
        
        # Compter les bourses
        cur.execute("SELECT COUNT(*) FROM bourses")
        count = cur.fetchone()[0]
        
        # Voir quelques bourses
        cur.execute("SELECT id, titre FROM bourses LIMIT 5")
        sample_bourses = cur.fetchall()
        
        # Voir les utilisateurs
        cur.execute("SELECT COUNT(*) FROM users")
        users_count = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return jsonify({
            'table_structure': [
                {'position': col[2], 'name': col[0], 'type': col[1]} 
                for col in columns
            ],
            'total_bourses': count,
            'total_users': users_count,
            'sample_bourses': [
                {'id': b[0], 'titre': b[1]}
                for b in sample_bourses
            ],
            'database_url': DATABASE_URL is not None
        })