# coding: utf-8
# edit_recipe.py - Logic for modifying existing recipes

from flask import render_template, request, redirect, url_for, g, abort
from create_recipe import normalize_german_text
from database import get_db  # <--- Hier importieren!

def show_edit_form(id):
    db = get_db()   
    recipe = db.execute("SELECT * FROM recipe WHERE recipe_id = ?", (id,)).fetchone()
    
    if recipe is None:
        abort(404)

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        servings = request.form.get('servings')
        
        title_norm = normalize_german_text(title)
        
        db.execute("""
            UPDATE recipe 
            SET title = ?, title_normalized = ?, description = ?, servings = ?
            WHERE recipe_id = ?
        """, (title, title_norm, description, servings, id))
        db.commit()
        
        return redirect(url_for('show_details', id=id))

    return render_template('recipe_form.html', recipe=recipe, is_edit=True)
