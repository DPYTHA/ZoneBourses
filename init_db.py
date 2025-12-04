#!/usr/bin/env python3
import sys
import os

# Ajoutez le répertoire courant au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Opportunity

with app.app_context():
    print("Création des tables...")
    db.create_all()
    print("✅ Tables créées")
    
    # Créer admin
    from config import Config
    admin = User.query.filter_by(email=Config.ADMIN_EMAIL).first()
    if not admin:
        admin = User(
            nom='Admin',
            prenom='System',
            numero='+7 9879040719',
            email=Config.ADMIN_EMAIL,
            password=Config.ADMIN_PASSWORD,
            is_admin=True,
            is_active=True
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin créé")
    
    print("Initialisation terminée!")