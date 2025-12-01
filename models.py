import psycopg
from datetime import datetime
from flask_login import UserMixin
# Ajouter cette fonction pour gérer l'upload des fichiers
import os
import uuid
from werkzeug.utils import secure_filename

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
        return f"/{filepath}"
    return None
# Configuration de la base de données PostgreSQL
DB_CONFIG = {
    'dbname': 'Minizone_db',
    'user': 'Zone_user',
    'password': 'Pytha1991',
    'host': 'localhost',
    'port': '5432'
}

def init_db():
    """Initialise la base de données avec les tables nécessaires"""
    conn = psycopg2.connect(**DB_CONFIG)
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
    
    # Création de la table des bourses - AVEC AJOUT DE COLONNE SI ELLE EXISTE DÉJÀ
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
    
    # AJOUT : Vérifier et ajouter la colonne is_active si elle n'existe pas
    try:
        cur.execute('''
            ALTER TABLE bourses 
            ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE
        ''')
    except Exception as e:
        print(f"Note: La colonne is_active existe peut-être déjà: {e}")
    
    # Créer l'admin par défaut
    cur.execute('''
        INSERT INTO users (nom, prenom, numero_whatsapp, email, password, is_admin, is_active)
        VALUES ('Admin', 'System', '+2250710069791', 'moua18978@gmail.com', 'admin123', TRUE, TRUE)
        ON CONFLICT (numero_whatsapp) DO NOTHING
    ''')
    
    # Insérer des bourses d'exemple - AJOUT DE is_active
    cur.execute('''
        INSERT INTO bourses (titre, description, pays, universite, niveau_etude, domaine_etude, montant_bourse, date_limite, conditions, procedure_postulation, image_url, is_active)
        VALUES 
        ('Bourse d''excellence en Informatique', 'Bourse complète pour étudier l''informatique en France', 'France', 'Université Paris-Saclay', 'Master', 'Informatique', '15 000€ par an', '2024-06-30', 'Diplôme de licence en informatique, moyenne minimale de 14/20', '1. Remplir le formulaire en ligne\n2. Envoyer les documents requis\n3. Passer un entretien', '/static/images/bourse1.jpg', TRUE),
        ('Bourse pour études en Génie Civil', 'Bourse partielle pour études de génie civil au Canada', 'Canada', 'Université de Montréal', 'Licence', 'Génie Civil', '10 000 CAD par an', '2024-07-15', 'Baccalauréat scientifique, bon niveau en mathématiques', '1. Créer un compte sur le portail de l''université\n2. Soumettre le dossier de candidature\n3. Attendre la réponse', '/static/images/bourse2.jpg', TRUE)
        ON CONFLICT DO NOTHING
    ''')
    
    conn.commit()
    cur.close()
    conn.close()

def get_db_connection():
    """Établit une connexion à la base de données"""
    return psycopg2.connect(**DB_CONFIG)

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
        cur = conn.cursor()
        cur.execute('SELECT id, nom, prenom, numero_whatsapp, password, email, is_active, is_admin, date_inscription FROM users WHERE numero_whatsapp = %s', (numero_whatsapp,))
        user_data = cur.fetchone()
        cur.close()
        conn.close()
        
        if user_data:
            return User(*user_data)
        return None
@app.route('/debug/check-db')
def debug_check_db():
    """Route de debug pour vérifier la structure de la base"""
    conn = get_db_connection()
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
    cur.execute("SELECT id, titre, procedure_medias FROM bourses LIMIT 5")
    sample_bourses = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return jsonify({
        'table_structure': [
            {'position': col[2], 'name': col[0], 'type': col[1]} 
            for col in columns
        ],
        'total_bourses': count,
        'sample_bourses': [
            {'id': b[0], 'titre': b[1], 'procedure_medias': str(b[2])}
            for b in sample_bourses
        ]
    })