# coding: utf-8
# view_recipe.py - Displays details, deletes recipes and allows fast updates

from flask import render_template, abort, request, redirect, url_for
from database import get_db

def delete_recipe(id):
    """ Deletes a recipe and all linked entries via Cascading """
    if request.method == 'POST':
        db = get_db()
        # Due to 'ON DELETE CASCADE' in the SQL schema, linked 
        # ingredients and steps are deleted automatically.
        db.execute("DELETE FROM recipe WHERE recipe_id = ?", (id,))
        db.commit()
    return redirect(url_for('kochbuch.index'))

def update_fast(id):
    """ Saves servings and annotations directly from the detail view """
    if request.method == 'POST':
        db = get_db()
        servings = request.form.get('servings')
        notes = request.form.get('notes') # Form field 'notes' -> DB column 'annotations'
        
        db.execute("UPDATE recipe SET servings = ?, annotations = ? WHERE recipe_id = ?", 
                   (servings, notes, id))
        db.commit()
    return redirect(url_for('kochbuch.show_details', id=id))

def show_details(id):
    db = get_db()
    
    # 1. Fetch core recipe data (including annotations and servings)
    recipe = db.execute("SELECT * FROM recipe WHERE recipe_id = ?", (id,)).fetchone()
    if recipe is None:
        abort(404)
        
    # 2. Load image with fallback to default.jpg
    image_row = db.execute("SELECT url FROM recipe_image WHERE recipe_id = ? LIMIT 1", (id,)).fetchone()
    # Use default image if no specific image is found in the database
    image_url = image_row['url'] if image_row else url_for('static', filename='images/default.jpg')

    # 3. Fetch ingredients with quantities, units, and names
    # Changed SQL to fetch unit name as 'unit_name' and ingredient name as 'ing_name'
    ingredients_sql = """
        SELECT ri.quantity, u.name AS unit_name, i.name AS ing_name, ri.preparation_note
        FROM recipe_ingredient ri
        JOIN ingredient i ON ri.ingredient_id = i.ingredient_id
        JOIN unit u ON ri.unit_id = u.unit_id
        WHERE ri.recipe_id = ?
        ORDER BY ri.position ASC
    """
    rows = db.execute(ingredients_sql, (id,)).fetchall()
    
    # Process rows to format numbers and handle names for the template
    ingredients = []
    for row in rows:
        qty = row['quantity']
        # Format quantity to remove unnecessary decimals (e.g., 250.0 -> 250)
        display_qty = f"{qty:g}".replace('.', ',') if qty else ""
        
        ingredients.append({
            'quantity': display_qty,
            'unit': row['unit_name'],
            'name': row['ing_name'],  # This provides the missing ingredient name
            'note': row['preparation_note']
        })
    
    # 4. Load instruction steps ordered by step number
    steps = db.execute("SELECT instruction FROM recipe_step WHERE recipe_id = ? ORDER BY step_no ASC", (id,)).fetchall()

    # 5. Load categories for display at the bottom
    categories = db.execute("""
        SELECT c.name FROM category c
        JOIN recipe_category rc ON c.category_id = rc.category_id
        WHERE rc.recipe_id = ?
    """, (id,)).fetchall()

    return render_template('recipe_detail.html', 
                           recipe=recipe, 
                           ingredients=ingredients, 
                           steps=steps,
                           categories=categories,
                           image_url=image_url)
