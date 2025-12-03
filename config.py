import os
import sys
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# ===========================================
# CONFIGURATION DE BASE
# ===========================================
class Config:
    """Configuration principale de l'application"""
    
    # ====================
    # CHEMIN DE BASE
    # ====================
    BASE_DIR = Path(__file__).parent.absolute()
    UPLOADS_DIR = BASE_DIR / "static" / "uploads"
    TEMPLATES_DIR = BASE_DIR / "templates"
    STATIC_DIR = BASE_DIR / "static"
    
    # ====================
    # SÉCURITÉ
    # ====================
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # ====================
    # ENVIRONNEMENT
    # ====================
    FLASK_ENV = os.environ.get("FLASK_ENV", "production")
    DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
    
    # ====================
    # BASE DE DONNÉES
    # ====================
    @property
    def SQLALCHEMY_DATABASE_URI(self):
        """Construire l'URI de la base de données"""
        # Priorité à DATABASE_URL (pour Railway/Heroku)
        if os.environ.get("DATABASE_URL"):
            db_url = os.environ.get("DATABASE_URL")
            # Convertir postgres:// en postgresql:// pour SQLAlchemy
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql://", 1)
            return db_url
        
        # Sinon, utiliser la configuration locale
        return f"postgresql://" \
               f"{os.environ.get('DB_USER', 'Zone_user')}:" \
               f"{os.environ.get('DB_PASSWORD', 'Pytha1991')}@" \
               f"{os.environ.get('DB_HOST', 'localhost')}:" \
               f"{os.environ.get('DB_PORT', '5432')}/" \
               f"{os.environ.get('DB_NAME', 'Minizone_db')}"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "max_overflow": 20,
        "connect_args": {
            "connect_timeout": 10,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        }
    }
    
    # ====================
    # UPLOAD DE FICHIERS
    # ====================
    UPLOAD_FOLDER = str(UPLOADS_DIR)
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_SIZE", 50)) * 1024 * 1024
    
    # Extensions autorisées
    ALLOWED_EXTENSIONS = {
        # Images
        "png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "ico",
        # Vidéos
        "mp4", "mov", "avi", "mkv", "webm", "flv", "wmv", "m4v",
        # Documents
        "pdf", "doc", "docx", "txt", "rtf", "odt",
        # Présentations
        "ppt", "pptx", "odp", "key",
        # Tableurs
        "xls", "xlsx", "ods", "csv",
        # Archives
        "zip", "rar", "7z", "tar", "gz"
    }
    
    # ====================
    # SESSION
    # ====================
    SESSION_TYPE = "filesystem"
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_USE_SIGNER = True
    SESSION_COOKIE_SECURE = not DEBUG  # HTTPS en production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    
    # ====================
    # CACHE
    # ====================
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    
    # ====================
    # LIMITES DE REQUÊTES
    # ====================
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_STORAGE_URL = "memory://"
    
    # ====================
    # ADMINISTRATION
    # ====================
    ADMIN_CONFIG = {
        "nom": os.environ.get("ADMIN_NOM", "Admin"),
        "prenom": os.environ.get("ADMIN_PRENOM", "System"),
        "numero_whatsapp": os.environ.get("ADMIN_PHONE", "+2250710069791"),
        "email": os.environ.get("ADMIN_EMAIL", "moua18978@gmail.com"),
        "password": os.environ.get("ADMIN_PASSWORD", "admin123")
    }
    
    # ====================
    # EMAIL (optionnel)
    # ====================
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@zonebourse.com")
    
    # ====================
    # WHATSAPP (optionnel)
    # ====================
    WHATSAPP_API_KEY = os.environ.get("WHATSAPP_API_KEY")
    WHATSAPP_PHONE_NUMBER = os.environ.get("WHATSAPP_PHONE_NUMBER")
    
    # ====================
    # ANALYTICS (optionnel)
    # ====================
    GOOGLE_ANALYTICS_ID = os.environ.get("GOOGLE_ANALYTICS_ID")
    
    # ====================
    # FONCTIONS UTILITAIRES
    # ====================
    @staticmethod
    def init_app(app):
        """Initialiser l'application avec cette configuration"""
        
        # Créer les dossiers nécessaires
        Config.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        Config.STATIC_DIR.mkdir(parents=True, exist_ok=True)
        Config.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        
        # Configurer l'application
        app.config.from_object(Config)
        
        # Ajouter des variables de template
        app.jinja_env.globals.update({
            "config": Config,
            "analytics_id": Config.GOOGLE_ANALYTICS_ID,
            "debug_mode": Config.DEBUG,
        })
        
        # Configurer les logs
        if Config.DEBUG:
            app.logger.setLevel("DEBUG")
        else:
            app.logger.setLevel("INFO")

# ===========================================
# CONFIGURATIONS SPÉCIFIQUES
# ===========================================
class DevelopmentConfig(Config):
    """Configuration pour le développement"""
    
    DEBUG = True
    FLASK_ENV = "development"
    
    # Désactiver HTTPS pour le développement
    SESSION_COOKIE_SECURE = False
    
    # Logs détaillés
    SQLALCHEMY_ECHO = True
    
class TestingConfig(Config):
    """Configuration pour les tests"""
    
    TESTING = True
    DEBUG = True
    FLASK_ENV = "testing"
    
    # Base de données de test
    SQLALCHEMY_DATABASE_URI = "postgresql://test_user:test_pass@localhost/test_db"
    WTF_CSRF_ENABLED = False
    
class ProductionConfig(Config):
    """Configuration pour la production"""
    
    DEBUG = False
    FLASK_ENV = "production"
    
    # Sécurité maximale
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Strict"
    
    # Performance
    SQLALCHEMY_ENGINE_OPTIONS = {
        **Config.SQLALCHEMY_ENGINE_OPTIONS,
        "pool_size": 20,
        "max_overflow": 30,
    }

# ===========================================
# SÉLECTION DE LA CONFIGURATION
# ===========================================
def get_config():
    """Retourner la configuration appropriée"""
    env = os.environ.get("FLASK_ENV", "production").lower()
    
    config_map = {
        "development": DevelopmentConfig,
        "testing": TestingConfig,
        "production": ProductionConfig,
    }
    
    return config_map.get(env, ProductionConfig)()

# ===========================================
# UTILITAIRES
# ===========================================
def check_environment():
    """Vérifier les variables d'environnement requises"""
    
    required_vars = ["SECRET_KEY"]
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Variables d'environnement manquantes:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n⚠️  Ajoutez-les dans le fichier .env")
        sys.exit(1)
    
    # Vérifier la clé secrète
    secret_key = os.environ.get("SECRET_KEY")
    if secret_key == "votre_cle_secrete_tres_longue_et_unique_changez_moi":
        print("⚠️  ATTENTION: Vous utilisez la clé secrète par défaut!")
        print("⚠️  Changez-la dans le fichier .env pour la production")
    
    print("✅ Configuration chargée avec succès")
    print(f"   Environnement: {os.environ.get('FLASK_ENV', 'production')}")
    print(f"   Debug: {os.environ.get('DEBUG', 'false')}")

# Vérifier l'environnement au chargement
if __name__ == "__main__":
    check_environment()