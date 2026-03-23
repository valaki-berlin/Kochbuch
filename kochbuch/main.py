# main.py - Core Flask Server
import os
import sqlite3
from flask import Flask, Blueprint, render_template, request, g
from werkzeug.middleware.proxy_fix import ProxyFix
from strings import TRANSLATIONS

from database import get_db

# Modular imports
import create_recipe
import view_recipe
import edit_recipe

DATABASE = 'rezepte/RezeptDB.db'

app = Flask(__name__)
@app.context_processor
def inject_globals():
    return dict(t=get_string)
def inject_translations():
    # Alles in diesem Dict ist automatisch in allen HTML-Dateien verfügbar
    return dict(t=get_string)

# Middleware für Proxy-Support (Nginx)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Blueprint für den Unterpfad /kochbuch
# kb = Blueprint('kochbuch', __name__, url_prefix='/kochbuch')
# kb = Blueprint('kochbuch', __name__, url_prefix='/kochbuch')

# Zu dem hier (Präfix entfernen):
kb = Blueprint('kochbuch', __name__)


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def get_string(key):
    lang = request.accept_languages.best_match(TRANSLATIONS.keys()) or 'en'
    return TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)

# --- Routen innerhalb des Blueprints ---

@kb.route('/')
def index():
    query = request.args.get('search', '')
    db = get_db()
    
    if query:
        sql = "SELECT recipe_id, title FROM recipe WHERE title_normalized LIKE ? "
        recipes = db.execute(sql, ('%' + query.lower() + '%',)).fetchall()
    else:
        recipes = db.execute("SELECT recipe_id, title FROM recipe").fetchall()

    return render_template('index.html', 
                           recipes=recipes, 
                           t=get_string, 
                           search_query=query)

# Register routes from other modules TO THE BLUEPRINT
kb.add_url_rule('/recipe/new', view_func=create_recipe.show_form, methods=['GET', 'POST'], endpoint='show_form')
kb.add_url_rule('/recipe/<int:id>', view_func=view_recipe.show_details, endpoint='show_details')
kb.add_url_rule('/recipe/<int:id>/edit', view_func=edit_recipe.show_edit_form, methods=['GET', 'POST'], endpoint='show_edit_form')
kb.add_url_rule('/recipe/<int:id>/delete', view_func=view_recipe.delete_recipe, methods=['POST'], endpoint='delete_recipe')
kb.add_url_rule('/import', view_func=lambda: "Import-Seite kommt bald!", endpoint='import_page')
# --- App Konfiguration ---

app.register_blueprint(kb)

if __name__ == '__main__':
    # Lokal zum Testen auf Port 5000, Gunicorn nutzt später Port 8000
    app.run(host='0.0.0.0', port=5000, debug=True)
