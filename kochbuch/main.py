# main.py - Core Flask Server
import os
import sqlite3
from flask import Flask, Blueprint, render_template, request, g, flash, redirect, url_for
from werkzeug.middleware.proxy_fix import ProxyFix 
from werkzeug.utils import secure_filename
from strings import TRANSLATIONS
from filter import build_filter_query

from database import get_db

# Modular imports
import view_recipe
import edit_recipe
import import_recipe

DATABASE = 'db/RezeptDB.db'

# Temporary directory for uploaded XML files
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
app.secret_key = 'super-secret-terminal-key-123'

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
    """
    Main index route that handles the multi-field search logic.
    Delegates SQL construction to filter.py.
    """
    db = get_db()
    
    # Get the individual search parameters from the GET request
    # These match the 'name' attributes in your index.html form
    search_title = request.args.get('title', '').strip()
    search_category = request.args.get('category', '').strip()
    search_ingredients = request.args.get('ingredients', '').strip()

    # Call the logic to build the SQL query and parameters
    query, params = build_filter_query(search_title, search_category, search_ingredients)

    # Execute the query and fetch all matching recipes
    recipes = db.execute(query, params).fetchall()

    # Note: We no longer need search_query=query, as index.html 
    # accesses parameters directly via request.args.get(...)
    return render_template('index.html', 
                           recipes=recipes, 
                           t=get_string)


def import_page():
    """Renders the upload form for XML import."""
    return render_template('import.html')

def do_import():
#    """Handles the XML file upload and calls the import logic."""
    if 'xml_file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('kochbuch.import_page'))
    
    file = request.files['xml_file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('kochbuch.import_page'))

    if file and file.filename.endswith('.xml'):
        # Save file to a secure temporary path
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        try:
            # Execute your existing import function
            # Ensure DATABASE variable contains the correct path to your SQLite file
            #xprint("call import_recipe.import_xml_to_db", flush=True)
            import_recipe.import_xml_to_db(filepath, DATABASE)
            flash('Import successful!', 'success')
        except Exception as e:
            print(f"Critical Error: {str(e)}", flush=True) # write to logfile      
            flash(f'Error during import: {str(e)}', 'danger')
        finally:
            # Clean up: remove the temporary file after processing
            if os.path.exists(filepath):
                os.remove(filepath)
                
        return redirect(url_for('kochbuch.index'))
    
    flash('Invalid file format. Please upload an XML file.', 'danger')
    return redirect(url_for('kochbuch.import_page'))

# Register routes from other modules TO THE BLUEPRINT

kb.add_url_rule('/recipe/new', 
                view_func=edit_recipe.manage_recipe, 
                methods=['GET', 'POST'], 
                endpoint='show_form')

kb.add_url_rule('/recipe/<int:id>/edit', 
                view_func=edit_recipe.manage_recipe, 
                methods=['GET', 'POST'], 
                endpoint='show_edit_form')

# Remaining routes
kb.add_url_rule('/recipe/<int:id>', 
                view_func=view_recipe.show_details, 
                endpoint='show_details')

kb.add_url_rule('/recipe/<int:id>/delete', 
                view_func=view_recipe.delete_recipe, 
                methods=['POST'], 
                endpoint='delete_recipe')

kb.add_url_rule('/import', 
                view_func=import_page, 
                methods=['GET'], 
                endpoint='import_page')

kb.add_url_rule('/do_import', 
                view_func=do_import, 
                methods=['POST'], 
                endpoint='do_import')

kb.add_url_rule('/recipe/fast_update/<int:id>', 
                view_func=view_recipe.update_fast, 
                methods=['POST'], 
                endpoint='update_fast')

# --- App Konfiguration ---

app.register_blueprint(kb)

if __name__ == '__main__':
    # Lokal zum Testen auf Port 5000, Gunicorn nutzt später Port 8000
    app.run(host='0.0.0.0', port=5000, debug=True)
