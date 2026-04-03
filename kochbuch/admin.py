# admin.py - Modular Administration Logic
from flask import render_template, request, redirect, url_for, flash
from database import get_db, DATABASE as DB_PATH
from strings import TRANSLATIONS
import utils  # Import for normalize_title
import export_xml


def admin_page():
    """Main route handler for the admin page."""
    db = get_db()
    # Get mode from the current URL
    mode = request.args.get('mode')
    
    if request.method == 'POST':
        action = request.form.get('action_mode')
        
        # We start with the current mode
        next_mode = mode 

        if action == 'edit':
            handle_edit(db)
        elif action == 'delete':
            handle_delete(db)
        elif action == 'export':
            handle_export()
            next_mode = None  # Signal to clear the mode
        elif action == 'purge':
            handle_purge(db)
            next_mode = None  # Signal to clear the mode

        # If next_mode is None, we redirect to the plain admin URL
        if next_mode is None:
            return redirect(url_for('kochbuch.admin_page'))
        
        # Otherwise, we keep the mode in the URL
        return redirect(url_for('kochbuch.admin_page', mode=next_mode))

    # GET logic
    categories = []
    if mode in ['edit', 'delete']:
        categories = db.execute("SELECT * FROM category ORDER BY name ASC").fetchall()

    return render_template('admin.html', mode=mode, categories=categories)
    
# --- Helper for Translations in Logic ---
def get_t(key):
    """Access strings.py directly for flash messages (defaults to German)."""
    # Note: If you have a session-based language, use it here instead of 'de'
    return TRANSLATIONS.get('de', {}).get(key, key)

# --- Action Functions ---

def handle_edit(db):
    """Updates category names for all selected items."""
    selected_ids = request.form.getlist('selected_items')
    all_ids = request.form.getlist('all_ids')
    new_names = request.form.getlist('category_names')
    
    updated_count = 0
    # Map IDs to their corresponding names via the full list index
    for i, cat_id in enumerate(all_ids):
        if cat_id in selected_ids:
            name = new_names[i].strip()
            if name:
                db.execute("UPDATE category SET name = ? WHERE category_id = ?", (name, cat_id))
                updated_count += 1

    db.commit()

def handle_delete(db):
    """Removes selected categories from the database."""
    selected_ids = request.form.getlist('selected_items')
    
    if not selected_ids:
        return

    # Use placeholders for safe SQL IN clause
    placeholders = ', '.join(['?'] * len(selected_ids))
    db.execute(f"DELETE FROM recipe_category WHERE category_id IN ({placeholders})", selected_ids)
    db.execute(f"DELETE FROM category WHERE category_id IN ({placeholders})", selected_ids)
    db.commit()
    

def handle_export():
    """Triggers the full XML export via export_xml.py."""
    try:
        # DB_PATH comes from database.DATABASE
        export_xml.export_database_to_xml(DB_PATH)
                
    except Exception as e:
        # Fallback if something goes wrong (e.g. write permissions)
        flash(f"Export Error: {str(e)}", "danger")

def handle_purge(db):
    """
    Cleans the database of orphaned entries (ingredients, units, categories)
    and re-normalizes all recipe titles for search consistency.
    """
    try:
        # 1. Delete orphaned ingredients (not linked to any recipe)
        db.execute("""
            DELETE FROM ingredient 
            WHERE ingredient_id NOT IN (SELECT DISTINCT ingredient_id FROM recipe_ingredient)
        """)

        # 2. Delete orphaned units (not linked to any recipe)
        db.execute("""
            DELETE FROM unit 
            WHERE unit_id NOT IN (SELECT DISTINCT unit_id FROM recipe_ingredient)
        """)

        # 3. Delete orphaned categories (not linked to any recipe)
        db.execute("""
            DELETE FROM category 
            WHERE category_id NOT IN (SELECT DISTINCT category_id FROM recipe_category)
        """)

        # 4. Refresh title normalization for all recipes
        # Fetching all recipes to process them with the Python utility function
        recipes = db.execute("SELECT recipe_id, title FROM recipe").fetchall()
        
        for recipe in recipes:
            new_norm_title = utils.normalize_title(recipe['title'])
            db.execute("""
                UPDATE recipe 
                SET title_normalized = ? 
                WHERE recipe_id = ?
            """, (new_norm_title, recipe['recipe_id']))

        db.commit()
        
    except Exception as e:
        db.rollback()
        # Fallback error message in case of DB lock or script errors
        flash(f"Purge Error: {str(e)}", "danger")