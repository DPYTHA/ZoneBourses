from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone
from config import Config
from flask_cors import CORS
import os
import sys

# Créer l'application Flask d'abord
app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']  # Important pour les sessions

CORS(app, supports_credentials=True, origins=["http://localhost:8081", "http://localhost:19000", "exp://*", "http://localhost:5000"])



# Configuration de la base de données avec validation
database_url = os.environ.get('DATABASE_URL', '')

if database_url:
    # Correction pour PostgreSQL sur Railway
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Fallback vers SQLite si DATABASE_URL n'est pas définie
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Importer Cloudinary APRÈS avoir configuré l'application
try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api
    
    # Configuration Cloudinary (uniquement si les variables existent)
    if all([
        app.config.get('CLOUDINARY_CLOUD_NAME'),
        app.config.get('CLOUDINARY_API_KEY'), 
        app.config.get('CLOUDINARY_API_SECRET')
    ]):
        cloudinary.config(
            cloud_name = app.config['CLOUDINARY_CLOUD_NAME'],
            api_key = app.config['CLOUDINARY_API_KEY'],
            api_secret = app.config['CLOUDINARY_API_SECRET'],
            secure = True
        )
        print("✅ Cloudinary configuré avec succès", file=sys.stderr)
    else:
        print("⚠️ Variables Cloudinary manquantes. L'upload d'images sera désactivé.", file=sys.stderr)
        
except ImportError:
    print("⚠️ Module Cloudinary non installé. L'upload d'images sera désactivé.", file=sys.stderr)
    # Définir des fonctions de secours
    cloudinary = None


# Modèle utilisateur
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    numero = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # Stocké en clair comme demandé
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    subscription_days = db.Column(db.Integer, default=0)  # Nouveau champ
    subscription_expiry = db.Column(db.DateTime)  # Nouveau champ
    created_at = db.Column(db.DateTime, server_default=db.func.now())

# Modèle pour les opportunités
class Opportunity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    pays = db.Column(db.String(100))
    montant = db.Column(db.String(100))
    deadline = db.Column(db.Date)
    is_featured = db.Column(db.Boolean, default=False)
    
    # Champs de postulation
    postulation_steps = db.Column(db.Text)  # Étapes séparées par |||
    documents_required = db.Column(db.Text)  # Documents séparés par |||
    postulation_link = db.Column(db.String(500))
    contact_email = db.Column(db.String(120))
    contact_phone = db.Column(db.String(50))
    
    # Images - stocker les URLs Cloudinary
    image_urls = db.Column(db.Text)  # URLs séparées par |||
    image_public_ids = db.Column(db.Text)  # IDs publics Cloudinary séparés par |||
    
    # Vidéo
    video_url = db.Column(db.String(500))
    
    created_at = db.Column(db.DateTime, server_default=db.func.now())
# ===== AJOUTEZ CE BLOC =====
# Initialisation automatique de la base de données
print("🚀 Initialisation de la base de données...", file=sys.stderr)
try:
    with app.app_context():
        # Créer toutes les tables
        db.create_all()
        print("✅ Tables SQLAlchemy créées", file=sys.stderr)
        
        # Vérifier/créer l'utilisateur admin
        admin = User.query.filter_by(email=app.config['ADMIN_EMAIL']).first()
        if not admin:
            admin = User(
                nom='Admin',
                prenom='System',
                numero='+7 9879040719',
                email=app.config['ADMIN_EMAIL'],
                password=app.config['ADMIN_PASSWORD'],
                is_admin=True,
                is_active=True,
                subscription_days=9999  # Admin a accès illimité
            )
            db.session.add(admin)
            db.session.commit()
            print(f"✅ Compte admin créé: {app.config['ADMIN_EMAIL']}", file=sys.stderr)
        else:
            print(f"✅ Compte admin existant: {admin.email}", file=sys.stderr)
        
        # Créer des opportunités d'exemple si vide
        if Opportunity.query.count() == 0:
            opportunities = [
                Opportunity(
                    title='Bourse Complète',
                    type='bourse',
                    description='Bourse d\'études complète pour programmes universitaires',
                    pays='France, Allemagne, Canada',
                    montant='1,18€ / mois',
                    is_featured=False
                ),
                # ... (ajoutez toutes vos opportunités ici)
            ]
            for opp in opportunities:
                db.session.add(opp)
            db.session.commit()
            print(f"✅ {len(opportunities)} opportunités créées", file=sys.stderr)
        else:
            print(f"✅ {Opportunity.query.count()} opportunités existantes", file=sys.stderr)
            
except Exception as e:
    print(f"❌ ERREUR lors de l'initialisation: {str(e)}", file=sys.stderr)
    # Ne pas lever l'exception pour éviter de bloquer le démarrage

print("✅ Initialisation de la base terminée", file=sys.stderr)


# Initialisation de la base
def init_db():
    with app.app_context():
        db.create_all()
        
        # Créer admin
        admin = User.query.filter_by(email=app.config['ADMIN_EMAIL']).first()
        if not admin:
            admin = User(
                nom='Admin',
                prenom='System',
                numero='+7 9879040719',
                email=app.config['ADMIN_EMAIL'],
                password=app.config['ADMIN_PASSWORD'],  # En clair
                is_admin=True,
                is_active=True
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin créé")
        
        # Créer opportunités d'exemple si vide
        if Opportunity.query.count() == 0:
            opportunities = [
                Opportunity(
                    title='Bourse Complète',
                    type='bourse',
                    description='Bourse d\'études complète pour programmes universitaires',
                    pays='France, Allemagne, Canada',
                    montant='1,18€ / mois',
                    is_featured=False
                ),
                Opportunity(
                    title='Bourse d\'Excellence Eiffel',
                    type='excellence',
                    description='Frais complets + Allocation de vie mensuelle',
                    pays='France',
                    montant='Complet',
                    is_featured=True  # Carte spéciale
                ),
                Opportunity(
                    title='Bourse Complète',
                    type='bourse',
                    description='Disponible dans 45 pays à travers le monde',
                    pays='International',
                    montant='45 PAYS',
                    is_featured=False
                ),
                Opportunity(
                    title='Bourses Admissions',
                    type='admission',
                    description='Admissions avec bourses d\'études intégrées',
                    pays='Monde',
                    montant='Variable',
                    is_featured=False
                ),
                Opportunity(
                    title='Fulbright Foreign Student',
                    type='bourse',
                    description='Programme d\'échange culturel et académique',
                    pays='États-Unis',
                    montant='Variable',
                    is_featured=False
                ),
                Opportunity(
                    title='Bourse d\'Excellence',
                    type='excellence',
                    description='Pour étudiants avec parcours académique exceptionnel',
                    pays='Europe, Amérique du Nord',
                    montant='2,500€ / mois',
                    is_featured=False
                )
            ]
            for opp in opportunities:
                db.session.add(opp)
            db.session.commit()
            print(f"✅ {len(opportunities)} opportunités créées")

# Routes principales
@app.route('/')
def splash():
    return render_template('splash.html')

@app.route('/home')
def home():
    return render_template('home.html')
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/admin/passwords')
def admin_passwords():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Accès réservé aux administrateurs.', 'error')
        return redirect(url_for('login'))
    
    users = User.query.all()
    return render_template('admin_passwords.html',
                         user={'nom': session['user_nom'], 'prenom': session['user_prenom']},
                         users=users)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            nom = request.form['nom']
            prenom = request.form['prenom']
            numero = request.form['numero']
            email = request.form['email']
            password = request.form['password']
            
            # Validation simple
            if not all([nom, prenom, numero, email, password]):
                flash('Tous les champs sont obligatoires', 'error')
                return redirect(url_for('register'))
            
            # Vérifier si l'utilisateur existe déjà
            if User.query.filter_by(numero=numero).first():
                flash('Ce numéro est déjà enregistré.', 'error')
                return redirect(url_for('register'))
            
            if User.query.filter_by(email=email).first():
                flash('Cet email est déjà enregistré.', 'error')
                return redirect(url_for('register'))
            
            # Créer nouvel utilisateur
            new_user = User(
                nom=nom,
                prenom=prenom,
                numero=numero,
                email=email,
                password=password,
                is_admin=False,
                is_active=False
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            flash('Inscription réussie! Votre compte est en attente d\'activation, success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de l\'inscription: {str(e)}', 'error')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        numero = request.form['numero']
        password = request.form['password']
        
        user = User.query.filter_by(numero=numero).first()
        
        if user:
            # Comparaison en clair comme demandé
            if user.password == password:
                if user.is_active:
                    session['user_id'] = user.id
                    session['user_nom'] = user.nom
                    session['user_prenom'] = user.prenom
                    session['is_admin'] = user.is_admin
                    
                    flash('Connexion réussie!', 'success')
                    
                    # Redirection différente pour admin vs utilisateur normal
                    if user.is_admin:
                        return redirect(url_for('admin_dashboard'))
                    else:
                        return redirect(url_for('dashboard'))
                        
                else:
                    flash('Votre compte est désactivé pour le moment ', 'error')
            else:
                flash('Mot de passe incorrect.', 'error')
        else:
            flash('Numéro de téléphone non reconnu.', 'error')
    
    return render_template('login.html')

@app.route('/admin/upload-image', methods=['POST'])
def upload_image():
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'success': False, 'error': 'Non autorisé'}), 403
    
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'Aucune image fournie'}), 400
    
    image_file = request.files['image']
    
    if image_file.filename == '':
        return jsonify({'success': False, 'error': 'Nom de fichier vide'}), 400
    
    try:
        # Récupérer le timestamp depuis la requête
        timestamp = request.form.get('timestamp')
        
        # Upload vers Cloudinary avec timestamp
        upload_result = cloudinary.uploader.upload(
            image_file,
            folder="zonebourse/opportunities",
            timestamp=timestamp if timestamp else None,
            transformation=[
                {'width': 1200, 'height': 800, 'crop': 'limit'},
                {'quality': 'auto:good'}
            ]
        )
        
        return jsonify({
            'success': True,
            'url': upload_result['secure_url'],
            'public_id': upload_result['public_id']
        })
        
    except Exception as e:
        print(f"Erreur Cloudinary: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Veuillez vous connecter pour accéder au tableau de bord.', 'error')
        return redirect(url_for('login'))
    
    # Récupérer toutes les opportunités
    opportunities = Opportunity.query.order_by(Opportunity.created_at.desc()).all()
    
    return render_template('dashboard.html', 
                         user={'nom': session['user_nom'], 'prenom': session['user_prenom']},
                         opportunities=opportunities)

@app.route('/logout')
def logout():
    session.clear()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('home'))

# Route pour vérifier la session (utile pour le splash screen)
@app.route('/check-session')
def check_session():
    return jsonify({
        'authenticated': 'user_id' in session,
        'is_admin': session.get('is_admin', False)
    })

# ==================== ADMIN ROUTES ====================

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Accès réservé aux administrateurs.', 'error')
        return redirect(url_for('login'))
    
    # Statistiques
    total_users = User.query.count()
    total_opportunities = Opportunity.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    
    # Dernières opportunités
    recent_opportunities = Opportunity.query.order_by(Opportunity.created_at.desc()).limit(5).all()
    
    return render_template('admin_dashboard.html',
                         user={'nom': session['user_nom'], 'prenom': session['user_prenom']},
                         stats={
                             'total_users': total_users,
                             'total_opportunities': total_opportunities,
                             'active_users': active_users
                         },
                         recent_opportunities=recent_opportunities)

@app.route('/admin/opportunities')
def admin_opportunities():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Accès réservé aux administrateurs.', 'error')
        return redirect(url_for('login'))
    
    opportunities = Opportunity.query.order_by(Opportunity.created_at.desc()).all()
    return render_template('admin_opportunities.html', 
                         user={'nom': session['user_nom'], 'prenom': session['user_prenom']},
                         opportunities=opportunities)

@app.route('/admin/opportunities/add', methods=['GET', 'POST'])
def admin_add_opportunity():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Accès réservé aux administrateurs.', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            # Récupération des champs de base
            title = request.form['title']
            type_opp = request.form['type']
            description = request.form['description']
            pays = request.form['pays']
            montant = request.form['montant']
            is_featured = 'is_featured' in request.form
            
            # Champs de postulation
            steps = request.form.getlist('steps[]')
            documents = request.form.getlist('documents[]')
            postulation_steps = '|||'.join(steps) if steps else ''
            documents_required = '|||'.join(documents) if documents else ''
            
            # Autres champs
            postulation_link = request.form.get('postulation_link', '')
            contact_email = request.form.get('contact_email', '')
            contact_phone = request.form.get('contact_phone', '')
            video_url = request.form.get('video_url', '')
            
            # Gestion de la date limite
            deadline_str = request.form.get('deadline', '')
            deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None
            
            # Gestion des images téléchargées
            uploaded_image_urls = []
            uploaded_public_ids = []
            
            # Traiter les fichiers uploadés
            if 'images[]' in request.files:
                image_files = request.files.getlist('images[]')
                for image_file in image_files:
                    if image_file and image_file.filename != '':
                        try:
                            # Upload vers Cloudinary
                            upload_result = cloudinary.uploader.upload(
                                image_file,
                                folder="zonebourse/opportunities",
                                transformation=[
                                    {'width': 1200, 'height': 800, 'crop': 'limit'},
                                    {'quality': 'auto:good'}
                                ]
                            )
                            uploaded_image_urls.append(upload_result['secure_url'])
                            uploaded_public_ids.append(upload_result['public_id'])
                        except Exception as upload_error:
                            print(f"Erreur d'upload Cloudinary: {upload_error}")
                            flash(f"Erreur avec l'image {image_file.filename}: {upload_error}", 'warning')
            
            # Convertir les listes en chaînes
            image_urls_str = '|||'.join(uploaded_image_urls)
            image_public_ids_str = '|||'.join(uploaded_public_ids)
            
            # Créer la nouvelle opportunité
            new_opportunity = Opportunity(
                title=title,
                type=type_opp,
                description=description,
                pays=pays,
                montant=montant,
                deadline=deadline,
                is_featured=is_featured,
                postulation_steps=postulation_steps,
                documents_required=documents_required,
                postulation_link=postulation_link,
                contact_email=contact_email,
                contact_phone=contact_phone,
                image_urls=image_urls_str,
                image_public_ids=image_public_ids_str,
                video_url=video_url
            )
            
            db.session.add(new_opportunity)
            db.session.commit()
            
            flash('Opportunité ajoutée avec succès!', 'success')
            return redirect(url_for('admin_opportunities'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur: {str(e)}', 'error')
    
    return render_template('admin_add_opportunity.html',
                         user={'nom': session['user_nom'], 'prenom': session['user_prenom']})

@app.route('/admin/delete-image/<public_id>', methods=['DELETE'])
def delete_image(public_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'success': False, 'error': 'Non autorisé'}), 403
    
    try:
        result = cloudinary.uploader.destroy(public_id)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/opportunities/edit/<int:id>', methods=['GET', 'POST'])
def admin_edit_opportunity(id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Accès réservé aux administrateurs.', 'error')
        return redirect(url_for('login'))
    
    opportunity = Opportunity.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            opportunity.title = request.form['title']
            opportunity.type = request.form['type']
            opportunity.description = request.form['description']
            opportunity.pays = request.form['pays']
            opportunity.montant = request.form['montant']
            opportunity.is_featured = 'is_featured' in request.form
            
            db.session.commit()
            flash('Opportunité mise à jour avec succès!', 'success')
            return redirect(url_for('admin_opportunities'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur: {str(e)}', 'error')
    
    return render_template('admin_edit_opportunity.html',
                         user={'nom': session['user_nom'], 'prenom': session['user_prenom']},
                         opportunity=opportunity)

@app.route('/admin/opportunities/delete/<int:id>', methods=['POST'])
def admin_delete_opportunity(id):
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'Non autorisé'}), 403
    
    try:
        opportunity = Opportunity.query.get_or_404(id)
        db.session.delete(opportunity)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/admin/toggle_user/<int:id>', methods=['POST'])
def admin_toggle_user(id):
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'Non autorisé'}), 403
    
    try:
        user = User.query.get_or_404(id)
        user.is_active = not user.is_active
        db.session.commit()
        return jsonify({'success': True, 'is_active': user.is_active})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# API pour récupérer les mots de passe en clair (admin seulement)
@app.route('/admin/passwords')
def get_passwords():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Accès réservé aux administrateurs.', 'error')
        return redirect(url_for('login'))
    
    users = User.query.with_entities(User.id, User.nom, User.prenom, User.numero, User.email, User.password).all()
    
    return render_template('admin_passwords.html', 
                         user={'nom': session['user_nom'], 'prenom': session['user_prenom']},
                         users=users)


# Routes pour la gestion des utilisateurs
@app.route('/admin/user/<int:id>/add-subscription-month', methods=['POST'])
def admin_add_subscription_month(id):
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'Non autorisé'}), 403
    
    try:
        user = User.query.get_or_404(id)
        
        # Ajouter 30 jours d'abonnement
        if user.subscription_days:
            user.subscription_days += 30
        else:
            user.subscription_days = 30
        
        # Mettre à jour la date d'expiration
        if user.subscription_expiry:
            user.subscription_expiry += timedelta(days=30)
        else:
            user.subscription_expiry = datetime.utcnow() + timedelta(days=30)
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'30 jours ajoutés à l\'abonnement de {user.prenom} {user.nom}'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/user/<int:id>/remove-subscription-month', methods=['POST'])
def admin_remove_subscription_month(id):
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'Non autorisé'}), 403
    
    try:
        user = User.query.get_or_404(id)
        
        # Enlever 30 jours d'abonnement (minimum 0)
        if user.subscription_days:
            user.subscription_days = max(0, user.subscription_days - 30)
        
        # Mettre à jour la date d'expiration
        if user.subscription_expiry:
            user.subscription_expiry = datetime.now(timezone.utc) + timedelta(days=30)
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'30 jours retirés de l\'abonnement de {user.prenom} {user.nom}'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/user/<int:id>/activate', methods=['POST'])
def admin_activate_user(id):
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'Non autorisé'}), 403
    
    try:
        user = User.query.get_or_404(id)
        user.is_active = True
        db.session.commit()
        return jsonify({'success': True, 'message': f'Utilisateur {user.prenom} {user.nom} activé'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/user/<int:id>/deactivate', methods=['POST'])
def admin_deactivate_user(id):
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'Non autorisé'}), 403
    
    try:
        user = User.query.get_or_404(id)
        user.is_active = False
        db.session.commit()
        return jsonify({'success': True, 'message': f'Utilisateur {user.prenom} {user.nom} désactivé'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/user/<int:id>/block', methods=['POST'])
def admin_block_user(id):
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'Non autorisé'}), 403
    
    try:
        user = User.query.get_or_404(id)
        user.is_blocked = True
        db.session.commit()
        return jsonify({'success': True, 'message': f'Utilisateur {user.prenom} {user.nom} bloqué'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/user/<int:id>/unblock', methods=['POST'])
def admin_unblock_user(id):
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'Non autorisé'}), 403
    
    try:
        user = User.query.get_or_404(id)
        user.is_blocked = False
        db.session.commit()
        return jsonify({'success': True, 'message': f'Utilisateur {user.prenom} {user.nom} débloqué'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


from datetime import datetime

@app.route('/opportunity/<int:opportunity_id>')
def opportunity_details(opportunity_id):
    """Afficher les détails complets d'une opportunité"""
    if 'user_id' not in session:
        flash('Veuillez vous connecter pour voir les détails.', 'error')
        return redirect(url_for('login'))
    
    # Récupérer l'opportunité
    opportunity = Opportunity.query.get_or_404(opportunity_id)
    
    # Récupérer l'utilisateur
    user = User.query.get(session['user_id'])
    
    # Traiter les étapes de postulation
    steps = []
    if opportunity.postulation_steps:
        steps = [step.strip() for step in opportunity.postulation_steps.split('|||') if step.strip()]
    
    # Traiter les documents requis
    documents = []
    if opportunity.documents_required:
        documents = [doc.strip() for doc in opportunity.documents_required.split('|||') if doc.strip()]
    
    # Traiter les images
    images = []
    if opportunity.image_urls:
        images = [img.strip() for img in opportunity.image_urls.split('|||') if img.strip()]
    
    # Récupérer d'autres opportunités similaires (pour la section "Autres opportunités")
    related_opportunities = Opportunity.query.filter(
        Opportunity.id != opportunity.id,
        Opportunity.type == opportunity.type
    ).limit(3).all()
    
    return render_template('opportunity_details.html',
                         opportunity=opportunity,
                         user={'nom': user.nom, 'prenom': user.prenom},
                         steps=steps,
                         documents=documents,
                         images=images,
                         related_opportunities=related_opportunities,
                         now=datetime.now())

@app.route('/admin/user/<int:id>/make-admin', methods=['POST'])
def admin_make_admin(id):
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'Non autorisé'}), 403
    
    try:
        user = User.query.get_or_404(id)
        user.is_admin = True
        db.session.commit()
        return jsonify({'success': True, 'message': f'Utilisateur {user.prenom} {user.nom} est maintenant administrateur'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Modifiez la route admin_users pour passer 'now'
@app.route('/admin/users')
def admin_users():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Accès réservé aux administrateurs.', 'error')
        return redirect(url_for('login'))
    
    users = User.query.all()
    return render_template('admin_users.html',
                         user={'nom': session['user_nom'], 'prenom': session['user_prenom']},
                         users=users,
                         now=datetime.utcnow())  # Ajoutez ceci

# ========== AJOUTER CES ROUTES API À LA FIN DE VOTRE app.py EXISTANT ==========
# (Ne supprimez RIEN de votre code actuel)

# ========== NOUVELLES ROUTES API POUR L'APPLICATION MOBILE ==========
# Ces routes sont indépendantes et n'affectent PAS vos routes web existantes

@app.route('/api/me', methods=['GET'])
def api_get_current_user():
    """Récupérer l'utilisateur connecté - Version API"""
    if 'user_id' not in session:
        return jsonify({'authenticated': False}), 401
    
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'authenticated': False}), 401
    
    return jsonify({
        'authenticated': True,
        'id': user.id,
        'nom': user.nom,
        'prenom': user.prenom,
        'numero': user.numero,
        'email': user.email,
        'is_admin': user.is_admin,
        'is_active': user.is_active,
        'subscription_days': user.subscription_days,
        'subscription_expiry': user.subscription_expiry.isoformat() if user.subscription_expiry else None
    })

@app.route('/api/login', methods=['POST'])
def api_login():
    """API de connexion pour l'application mobile - Version API"""
    data = request.get_json()
    numero = data.get('numero')
    password = data.get('password')
    
    user = User.query.filter_by(numero=numero).first()
    
    if user and user.password == password:
        if user.is_active:
            session['user_id'] = user.id
            session['user_nom'] = user.nom
            session['user_prenom'] = user.prenom
            session['user_numero'] = user.numero
            session['is_admin'] = user.is_admin
            
            # CORRECTION : Convertir is_admin en booléen
            is_admin_value = bool(user.is_admin) if user.is_admin is not None else False
            
            return jsonify({
                'success': True,
                'user': {
                    'id': user.id,
                    'nom': user.nom,
                    'prenom': user.prenom,
                    'numero': user.numero,
                    'email': user.email,
                    'is_admin': is_admin_value  # ← Force en booléen True/False
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Compte désactivé'}), 401
    else:
        return jsonify({'success': False, 'error': 'Numéro ou mot de passe incorrect'}), 401
@app.route('/api/register', methods=['POST'])
def api_register():
    """API d'inscription pour l'application mobile - Version API"""
    data = request.get_json()
    
    nom = data.get('nom')
    prenom = data.get('prenom')
    numero = data.get('numero')
    email = data.get('email')
    password = data.get('password')
    
    # Validation
    if not all([nom, prenom, numero, email, password]):
        return jsonify({'success': False, 'error': 'Tous les champs sont obligatoires'}), 400
    
    if User.query.filter_by(numero=numero).first():
        return jsonify({'success': False, 'error': 'Ce numéro est déjà enregistré'}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'error': 'Cet email est déjà enregistré'}), 400
    
    new_user = User(
        nom=nom,
        prenom=prenom,
        numero=numero,
        email=email,
        password=password,
        is_admin=False,
        is_active=True
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Inscription réussie'})

@app.route('/api/logout', methods=['POST'])
def api_logout():
    """API de déconnexion"""
    session.clear()
    return jsonify({'success': True})

@app.route('/api/opportunities', methods=['GET'])
def api_get_opportunities():
    """Récupérer toutes les opportunités - Version API"""
    opportunities = Opportunity.query.order_by(Opportunity.created_at.desc()).all()
    
    return jsonify({
        'opportunities': [{
            'id': opp.id,
            'title': opp.title,
            'type': opp.type,
            'description': opp.description[:200] + '...' if len(opp.description) > 200 else opp.description,
            'pays': opp.pays,
            'montant': opp.montant,
            'is_featured': opp.is_featured,
            'image_urls': opp.image_urls,
            'deadline': opp.deadline.isoformat() if opp.deadline else None,
            'created_at': opp.created_at.isoformat()
        } for opp in opportunities]
    })

@app.route('/api/opportunities/<int:opportunity_id>', methods=['GET'])
def api_get_opportunity_detail(opportunity_id):
    """Récupérer les détails complets d'une opportunité - Version API"""
    opportunity = Opportunity.query.get_or_404(opportunity_id)
    
    # Traiter les listes
    images = opportunity.image_urls.split('|||') if opportunity.image_urls else []
    steps = opportunity.postulation_steps.split('|||') if opportunity.postulation_steps else []
    documents = opportunity.documents_required.split('|||') if opportunity.documents_required else []
    
    return jsonify({
        'id': opportunity.id,
        'title': opportunity.title,
        'type': opportunity.type,
        'description': opportunity.description,
        'pays': opportunity.pays,
        'montant': opportunity.montant,
        'deadline': opportunity.deadline.isoformat() if opportunity.deadline else None,
        'is_featured': opportunity.is_featured,
        'images': images,
        'postulation_steps': steps,
        'documents_required': documents,
        'postulation_link': opportunity.postulation_link,
        'contact_email': opportunity.contact_email,
        'contact_phone': opportunity.contact_phone,
        'video_url': opportunity.video_url,
        'created_at': opportunity.created_at.isoformat()
    })

@app.route('/api/opportunities/featured', methods=['GET'])
def api_get_featured_opportunities():
    """Récupérer les opportunités en vedette - Version API"""
    featured = Opportunity.query.filter_by(is_featured=True).order_by(Opportunity.created_at.desc()).limit(5).all()
    
    return jsonify({
        'opportunities': [{
            'id': opp.id,
            'title': opp.title,
            'type': opp.type,
            'description': opp.description[:150] + '...' if len(opp.description) > 150 else opp.description,
            'pays': opp.pays,
            'montant': opp.montant,
            'image_urls': opp.image_urls
        } for opp in featured]
    })

@app.route('/api/opportunities/by-type/<string:type>', methods=['GET'])
def api_get_opportunities_by_type(type):
    """Récupérer les opportunités par catégorie - Version API"""
    opportunities = Opportunity.query.filter_by(type=type).order_by(Opportunity.created_at.desc()).all()
    
    return jsonify({
        'opportunities': [{
            'id': opp.id,
            'title': opp.title,
            'type': opp.type,
            'description': opp.description[:200] + '...' if len(opp.description) > 200 else opp.description,
            'pays': opp.pays,
            'montant': opp.montant,
            'image_urls': opp.image_urls,
            'deadline': opp.deadline.isoformat() if opp.deadline else None
        } for opp in opportunities]
    })

@app.route('/api/stats', methods=['GET'])
def api_get_stats():
    """Récupérer les statistiques pour l'accueil - Version API"""
    total_opportunities = Opportunity.query.count()
    featured_count = Opportunity.query.filter_by(is_featured=True).count()
    
    all_pays = Opportunity.query.with_entities(Opportunity.pays).all()
    unique_pays = len(set([p[0] for p in all_pays if p[0]]))
    
    total_users = User.query.count()
    
    return jsonify({
        'total_opportunities': total_opportunities,
        'unique_pays': unique_pays or 45,
        'total_users': total_users,
        'featured_count': featured_count
    })

@app.route('/api/categories', methods=['GET'])
def api_get_categories():
    """Récupérer les catégories avec comptage - Version API"""
    categories = [
        {'id': 'bourse', 'name': 'Bourses', 'icon': 'school', 'description': 'Bourses d\'études'},
        {'id': 'excellence', 'name': 'Excellence', 'icon': 'star', 'description': 'Programmes d\'excellence'},
        {'id': 'admission', 'name': 'Admissions', 'icon': 'book-open', 'description': 'Admissions universitaires'}
    ]
    
    for cat in categories:
        cat['count'] = Opportunity.query.filter_by(type=cat['id']).count()
    
    return jsonify({'categories': categories})

@app.route('/api/check-session', methods=['GET'])
def api_check_session():
    """Vérifier la session - Version API"""
    return jsonify({
        'authenticated': 'user_id' in session,
        'is_admin': session.get('is_admin', False),
        'user': {
            'nom': session.get('user_nom'),
            'prenom': session.get('user_prenom'),
            'numero': session.get('user_numero')
        } if 'user_id' in session else None
    })


# app.py - Ajoutez ces routes

@app.route('/api/user/data', methods=['GET'])
def get_user_data():
    """Récupérer les données personnelles de l'utilisateur"""
    if 'user_id' not in session:
        return jsonify({'error': 'Non authentifié'}), 401
    
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'Utilisateur non trouvé'}), 404
    
    return jsonify({
        'nom': user.nom,
        'prenom': user.prenom,
        'email': user.email,
        'numero': user.numero,
        'created_at': user.created_at.isoformat(),
        'subscription_days': user.subscription_days,
    })

@app.route('/api/user/delete', methods=['DELETE'])
def delete_user_account():
    """Supprimer définitivement le compte utilisateur"""
    if 'user_id' not in session:
        return jsonify({'error': 'Non authentifié'}), 401
    
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'Utilisateur non trouvé'}), 404
    
    try:
        # Supprimer l'utilisateur
        db.session.delete(user)
        db.session.commit()
        
        # Nettoyer la session
        session.clear()
        
        return jsonify({'success': True, 'message': 'Compte supprimé avec succès'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
    # app.py - Routes admin API

@app.route('/admin/api/stats', methods=['GET'])
def admin_api_stats():
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'Non autorisé'}), 403
    
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_opportunities = Opportunity.query.count()
    featured_opportunities = Opportunity.query.filter_by(is_featured=True).count()
    
    return jsonify({
        'totalUsers': total_users,
        'activeUsers': active_users,
        'totalOpportunities': total_opportunities,
        'featuredOpportunities': featured_opportunities,
    })

@app.route('/admin/api/users', methods=['GET'])
def admin_api_users():
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'Non autorisé'}), 403
    
    users = User.query.all()
    return jsonify({
        'users': [{
            'id': u.id,
            'nom': u.nom,
            'prenom': u.prenom,
            'email': u.email,
            'numero': u.numero,
            'is_admin': u.is_admin,
            'is_active': u.is_active,
            'created_at': u.created_at.isoformat(),
        } for u in users]
    })

if __name__ == '__main__':
    init_db()
    print("=" * 50)
    print("Serveur ZoneBourse démarré")
    print("=" * 50)
    print("URLs disponibles:")
    print("  - http://localhost:5000/ (splash)")
    print("  - http://localhost:5000/home (accueil)")
    print("  - http://localhost:5000/register (inscription)")
    print("  - http://localhost:5000/login (connexion)")
    print("  - http://localhost:5000/dashboard (tableau de bord utilisateur)")
    print("  - http://localhost:5000/admin/dashboard (tableau de bord admin)")
    print("  - http://localhost:5000/admin/opportunities (gestion opportunités)")
    print("  - http://localhost:5000/admin/users (gestion utilisateurs)")
    print("=" * 50)
    print(f"Admin par défaut:")
    print(f"  Email: {app.config['ADMIN_EMAIL']}")
    print(f"  Mot de passe: {app.config['ADMIN_PASSWORD']}")
    print("=" * 50)
    app.run(debug=True, port=5000)