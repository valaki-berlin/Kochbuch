# coding: utf-8
# view_recipe.py - Displays full recipe details
from flask import render_template, g, abort, request, redirect, url_for
from database import get_db  # <--- Hier importieren!

def delete_recipe(id):
    if request.method == 'POST':
        db = get_db()
        db.execute("DELETE FROM recipe_ingredient WHERE recipe_id = ?", (id,))
        db.execute("DELETE FROM recipe_step WHERE recipe_id = ?", (id,))
        db.execute("DELETE FROM recipe WHERE recipe_id = ?", (id,))
        db.commit()
    return redirect(url_for('kochbuch.index'))

def show_details(id):
    # from main import get_db  # Lokaler Import um Circular Imports zu vermeiden
    db = get_db()
    
    # 1. Fetch core recipe data
    recipe = db.execute("SELECT * FROM recipe WHERE recipe_id = ?", (id,)).fetchone()
    
    if recipe is None:
        abort(404)
        

    # 1.5 - fetch the first image, if existing 
    image_row = db.execute("SELECT url FROM recipe_image WHERE recipe_id = ? LIMIT 1", (id,)).fetchone()
    image_url = image_row['url'] if image_row else None

    # 2. Fetch ingredients with units using JOINs
    ingredients_sql = """
        SELECT ri.quantity, u.symbol, i.name, ri.preparation_note
        FROM recipe_ingredient ri
        JOIN ingredient i ON ri.ingredient_id = i.ingredient_id
        JOIN unit u ON ri.unit_id = u.unit_id
        WHERE ri.recipe_id = ?
        ORDER BY ri.position ASC
    """
    ingredients = db.execute(ingredients_sql, (id,)).fetchall()
    
    # 3. Fetch steps
    steps = db.execute("SELECT instruction FROM recipe_step WHERE recipe_id = ? ORDER BY step_id ASC", (id,)).fetchall()

    return render_template('recipe_detail.html', 
                           recipe=recipe, 
                           ingredients=ingredients, 
                           steps=steps)
