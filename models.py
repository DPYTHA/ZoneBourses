import os
import psycopg2
import json
from flask_login import UserMixin
import uuid

# Suppression de la fonction get_db_connection en double
# Cette fonction est déjà définie dans app.py
# Laissons Flask gérer une seule instance de connexion

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'mkv', 'pdf', 'doc', 'docx'}

def allowed_file(filename):
    """Vérifie si le fichier a une extension autorisée"""
    if not filename or '.' not in filename:
        return False
    return filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file):
    """Sauvegarde un fichier uploadé et retourne son chemin relatif"""
    if not file or not file.filename or file.filename == '':
        return None
    
    if allowed_file(file.filename):
        # Créer le dossier s'il n'existe pas
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Générer un nom de fichier unique
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{file_ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        try:
            file.save(filepath)
            print(f"✅ Fichier sauvegardé: {filename}")
            return f"/static/uploads/{filename}"
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde du fichier: {e}")
            return None
    else:
        print(f"❌ Format de fichier non autorisé: {file.filename}")
        return None

class User(UserMixin):
    """Classe utilisateur pour Flask-Login"""
    
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
        """Propriété pour vérifier si l'utilisateur est actif"""
        return self._is_active

    def get_id(self):
        """Retourne l'ID de l'utilisateur sous forme de chaîne"""
        return str(self.id)

    @staticmethod
    def get_by_id(user_id):
        """Récupère un utilisateur par son ID"""
        from app import get_db_connection  # Importation locale pour éviter les dépendances circulaires
        
        conn = get_db_connection()
        if conn is None:
            return None
        
        try:
            cur = conn.cursor()
            cur.execute(
                'SELECT id, nom, prenom, numero_whatsapp, password, email, is_active, is_admin, date_inscription '
                'FROM users WHERE id = %s',
                (user_id,)
            )
            user_data = cur.fetchone()
            cur.close()
            conn.close()
            
            if user_data:
                return User(*user_data)
            return None
        except Exception as e:
            print(f"Erreur lors de la récupération de l'utilisateur: {e}")
            return None

    @staticmethod
    def get_by_whatsapp(numero_whatsapp):
        """Récupère un utilisateur par son numéro WhatsApp"""
        from app import get_db_connection  # Importation locale pour éviter les dépendances circulaires
        
        conn = get_db_connection()
        if conn is None:
            return None
        
        try:
            cur = conn.cursor()
            cur.execute(
                'SELECT id, nom, prenom, numero_whatsapp, password, email, is_active, is_admin, date_inscription '
                'FROM users WHERE numero_whatsapp = %s',
                (numero_whatsapp,)
            )
            user_data = cur.fetchone()
            cur.close()
            conn.close()
            
            if user_data:
                return User(*user_data)
            return None
        except Exception as e:
            print(f"Erreur lors de la récupération de l'utilisateur par WhatsApp: {e}")
            return None

    def to_dict(self):
        """Convertit l'utilisateur en dictionnaire pour JSON"""
        return {
            'id': self.id,
            'nom': self.nom,
            'prenom': self.prenom,
            'numero_whatsapp': self.numero_whatsapp,
            'email': self.email,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'date_inscription': self.date_inscription.isoformat() if self.date_inscription else None
        }

class Bourse:
    """Classe représentant une bourse (optionnel - pour une abstraction future)"""
    
    def __init__(self, id, titre, description, pays, universite, niveau_etude, 
                 domaine_etude, montant_bourse, date_limite, conditions, 
                 procedure_postulation, image_url, video_url, procedure_medias, 
                 date_publication, is_active):
        self.id = id
        self.titre = titre
        self.description = description
        self.pays = pays
        self.universite = universite
        self.niveau_etude = niveau_etude
        self.domaine_etude = domaine_etude
        self.montant_bourse = montant_bourse
        self.date_limite = date_limite
        self.conditions = conditions
        self.procedure_postulation = procedure_postulation
        self.image_url = image_url
        self.video_url = video_url
        self.procedure_medias = procedure_medias
        self.date_publication = date_publication
        self.is_active = is_active

    @staticmethod
    def get_all_active():
        """Récupère toutes les bourses actives"""
        from app import get_db_connection
        
        conn = get_db_connection()
        if conn is None:
            return []
        
        try:
            cur = conn.cursor()
            cur.execute(
                'SELECT * FROM bourses WHERE is_active = TRUE ORDER BY date_limite ASC'
            )
            bourses_data = cur.fetchall()
            cur.close()
            conn.close()
            
            bourses = []
            for bourse in bourses_data:
                # Parser les médias de procédure
                procedure_medias = []
                if bourse[13]:  # Index 13 pour procedure_medias
                    try:
                        if isinstance(bourse[13], str):
                            procedure_medias = json.loads(bourse[13])
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
                    'date_limite': bourse[8],
                    'conditions': bourse[9],
                    'procedure_postulation': bourse[10],
                    'image_url': bourse[11],
                    'video_url': bourse[12],
                    'procedure_medias': procedure_medias,
                    'date_publication': bourse[14],
                    'is_active': bourse[15]
                })
            
            return bourses
            
        except Exception as e:
            print(f"Erreur lors de la récupération des bourses: {e}")
            return []

def create_debug_route(app):
    """Crée une route de debug pour vérifier l'état du système"""
    
    @app.route('/debug/models-status')
    def debug_models_status():
        """Route de debug pour vérifier l'état des modèles"""
        try:
            from app import get_db_connection
            
            conn = get_db_connection()
            if conn is None:
                return json.dumps({
                    'status': 'error',
                    'message': 'Connexion DB impossible'
                }, ensure_ascii=False, indent=2), 500
            
            cur = conn.cursor()
            
            # Vérifier la table users
            cur.execute("SELECT COUNT(*) FROM users")
            users_count = cur.fetchone()[0]
            
            # Vérifier la table bourses
            cur.execute("SELECT COUNT(*) FROM bourses")
            bourses_count = cur.fetchone()[0]
            
            # Vérifier les colonnes de bourses
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'bourses' 
                ORDER BY ordinal_position
            """)
            columns = cur.fetchall()
            
            cur.close()
            conn.close()
            
            result = {
                'status': 'success',
                'models_loaded': True,
                'database': {
                    'users_count': users_count,
                    'bourses_count': bourses_count,
                    'bourses_columns': [
                        {'name': col[0], 'type': col[1]} 
                        for col in columns
                    ]
                },
                'upload_config': {
                    'folder': UPLOAD_FOLDER,
                    'allowed_extensions': list(ALLOWED_EXTENSIONS),
                    'folder_exists': os.path.exists(UPLOAD_FOLDER)
                }
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                'status': 'error',
                'message': f'Erreur: {str(e)}'
            }, ensure_ascii=False, indent=2), 500

# Fonctions utilitaires pour gérer les médias
def parse_procedure_medias(medias_str):
    """Parse les médias de procédure depuis une chaîne JSON"""
    if not medias_str:
        return []
    
    try:
        if isinstance(medias_str, str):
            return json.loads(medias_str)
        elif isinstance(medias_str, (list, dict)):
            return medias_str
        else:
            return []
    except json.JSONDecodeError:
        print(f"Erreur de parsing JSON pour les médias: {medias_str}")
        return []

def save_multiple_files(files_list):
    """Sauvegarde plusieurs fichiers et retourne leurs chemins"""
    saved_files = []
    
    for file in files_list:
        if file and file.filename:
            file_url = save_uploaded_file(file)
            if file_url:
                # Déterminer le type de fichier
                filename_lower = file.filename.lower()
                if filename_lower.endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')):
                    file_type = 'video'
                elif filename_lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                    file_type = 'image'
                elif filename_lower.endswith(('.pdf',)):
                    file_type = 'pdf'
                elif filename_lower.endswith(('.doc', '.docx')):
                    file_type = 'document'
                else:
                    file_type = 'file'
                
                saved_files.append({
                    'url': file_url,
                    'type': file_type,
                    'filename': file.filename
                })
    
    return saved_files

# Initialisation du dossier d'upload au chargement du module
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
print(f"📁 Dossier d'upload vérifié: {UPLOAD_FOLDER}")