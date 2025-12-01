#!/bin/bash
echo "🔧 Installation des dépendances..."
pip install --upgrade pip
pip install Flask==2.3.3
pip install Flask-Login==0.6.3
pip install psycopg2-binary==2.9.9
pip install gunicorn==21.2.0
echo "✅ Dépendances installées"