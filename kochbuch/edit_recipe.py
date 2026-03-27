# coding: utf-8
from flask import render_template, request, redirect, url_for
from database import get_db
from utils import get_complete_recipe, save_complete_recipe, handle_image_upload

UPLOAD_FOLDER = 'static/recipe_images'

def manage_recipe(id=None):
    """
    Handles both creating a new recipe and editing an existing one.
    Consolidates data from recipe, ingredients, steps, category and images.
    """
    db = get_db()
    
    # 1. POST: Save data (Create or Update)
    if request.method == 'POST':
        try:
            if id is None:
                # Create mode: generate new ID first
                cursor = db.execute("INSERT INTO recipe (title, title_normalized) VALUES (?, ?)", ("New Recipe","PLaceholder"))
                id = cursor.lastrowid
            
            # Save all form data (centralized in utils)
            save_complete_recipe(db, id, request.form)
            
            # Handle image (centralized in utils)
            handle_image_upload(id, db, request.files, UPLOAD_FOLDER)
            
            db.commit()
            return redirect(url_for('kochbuch.show_details', id=id))
        except Exception as e:
            db.rollback()
            return f"Error saving recipe: {str(e)}", 500

    # 2. GET: Show form
    recipe_data = None
    if id is not None:
        # Edit mode: load existing data
        recipe_data = get_complete_recipe(db, id)
        if not recipe_data:
            return "Recipe not found", 404

    # Fetch master data for datalists (always needed)
    master_data = {
        'units': db.execute("SELECT DISTINCT name FROM unit ORDER BY name ASC").fetchall(),
        'ingredients': db.execute("SELECT DISTINCT name FROM ingredient ORDER BY name ASC").fetchall(),
        'categories': db.execute("SELECT DISTINCT name FROM category ORDER BY name ASC").fetchall()
    }

    return render_template('recipe_form.html', 
                           recipe=recipe_data, 
                           master_data=master_data)
