# coding: utf-8
from flask import render_template, request, redirect, url_for, flash
from database import get_db
import re

def manage_recipe(id=None):
    """
    Handles both creating a new recipe and editing an existing one.
    Consolidates data from recipe, ingredients, steps, category and images.
    """
    db = get_db()
    recipe = None
    ingredients = []
    steps_text = ""
    category_name = ""
    image_url = ""

    # 1. LOAD DATA (for Edit Mode)
    if id:
        recipe = db.execute("SELECT * FROM recipe WHERE recipe_id = ?", (id,)).fetchone()
        
        if recipe:
            # Load associated category
            cat_row = db.execute("""SELECT c.name FROM category c 
                                    JOIN recipe_category rc ON c.category_id = rc.category_id 
                                    WHERE rc.recipe_id = ? LIMIT 1""", (id,)).fetchone()
            category_name = cat_row['name'] if cat_row else ""
            
            # Load primary image
            img_row = db.execute("SELECT url FROM recipe_image WHERE recipe_id = ? LIMIT 1", (id,)).fetchone()
            image_url = img_row['url'] if img_row else ""

            # Load steps and join them with double newlines for the shared textarea
            step_rows = db.execute("SELECT instruction FROM recipe_step WHERE recipe_id = ? ORDER BY step_no ASC", (id,)).fetchall()
            steps_text = "\n\n".join([row['instruction'] for row in step_rows])

            # Load ingredients with units and names
            ingredients = db.execute("""
                SELECT ri.quantity, u.name as unit, i.name as ing_name
                FROM recipe_ingredient ri
                JOIN ingredient i ON ri.ingredient_id = i.ingredient_id
                JOIN unit u ON ri.unit_id = u.unit_id
                WHERE ri.recipe_id = ? ORDER BY ri.position ASC
            """, (id,)).fetchall()

    # 2. SAVE DATA (POST Request)
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        servings = request.form.get('servings') or 2
        
        # Handle the "is_tested" checkbox (checkboxes only send 'on' if checked)
        is_tested = 1 if request.form.get('is_tested') == 'on' else 0
        
        cat_input = request.form.get('category')
        img_input = request.form.get('image_url')
        raw_steps = request.form.get('steps_text', '')

        # A) Save or Update Main Recipe
        if id:
            db.execute("""UPDATE recipe 
                          SET title=?, title_normalized=?, description=?, servings=?, is_tested=? 
                          WHERE recipe_id=?""",
                       (title, title.lower(), description, servings, is_tested, id))
            rid = id
        else:
            # Prevent duplicate titles on creation
            existing = db.execute("SELECT recipe_id FROM recipe WHERE title = ? COLLATE NOCASE", (title,)).fetchone()
            if existing:
                flash("Error: A recipe with this title already exists!")
                # Return to form with previous input values
                return render_template('recipe_form.html', recipe=request.form, ingredients=[], 
                                       steps_text=raw_steps, category_name=cat_input, image_url=img_input)
            
            cur = db.execute("""INSERT INTO recipe (title, title_normalized, description, servings, is_tested) 
                                VALUES (?, ?, ?, ?, ?)""",
                             (title, title.lower(), description, servings, is_tested))
            rid = cur.lastrowid

        # B) Handle Category (Delete existing link and create new)
        db.execute("DELETE FROM recipe_category WHERE recipe_id = ?", (rid,))
        if cat_input:
            db.execute("INSERT OR IGNORE INTO category (name) VALUES (?)", (cat_input,))
            cid = db.execute("SELECT category_id FROM category WHERE name=?", (cat_input,)).fetchone()[0]
            db.execute("INSERT INTO recipe_category (recipe_id, category_id) VALUES (?,?)", (rid, cid))

        # C) Handle Image
        db.execute("DELETE FROM recipe_image WHERE recipe_id = ?", (rid,))
        if img_input:
            db.execute("INSERT INTO recipe_image (recipe_id, url, is_primary) VALUES (?, ?, 1)", (rid, img_input))

        # D) Handle Steps (Delete then parse and Insert)
        db.execute("DELETE FROM recipe_step WHERE recipe_id = ?", (rid,))
        processed_steps = re.split(r'\n\s*\n', raw_steps.strip())
        step_counter = 1
        for block in processed_steps:
            clean_block = block.strip()
            if clean_block:
                db.execute("INSERT INTO recipe_step (recipe_id, step_no, instruction) VALUES (?, ?, ?)",
                           (rid, step_counter, clean_block))
                step_counter += 1

        # E) Handle Ingredients (Delete and Re-insert logic)
        db.execute("DELETE FROM recipe_ingredient WHERE recipe_id = ?", (rid,))
        qtys = request.form.getlist('qty')
        units = request.form.getlist('unit')
        names = request.form.getlist('ing_name')
        
        for i in range(len(names)):
            if names[i].strip():
                # Ensure unit and ingredient exist in master tables
                db.execute("INSERT OR IGNORE INTO unit (name) VALUES (?)", (units[i],))
                db.execute("INSERT OR IGNORE INTO ingredient (name) VALUES (?)", (names[i],))
                
                u_id = db.execute("SELECT unit_id FROM unit WHERE name=?", (units[i],)).fetchone()[0]
                i_id = db.execute("SELECT ingredient_id FROM ingredient WHERE name=?", (names[i],)).fetchone()[0]
                
                db.execute("""INSERT INTO recipe_ingredient (recipe_id, ingredient_id, unit_id, quantity, position) 
                              VALUES (?,?,?,?,?)""", 
                           (rid, i_id, u_id, qtys[i].replace(',', '.'), i+1))

        db.commit()
        return redirect(url_for('kochbuch.show_details', id=rid))

    # 3. PREPARE FORM (GET Request)
    # Fetch master data for autocompletion
    all_units = db.execute("SELECT DISTINCT name FROM unit WHERE name != '' ORDER BY name ASC").fetchall()
    all_ingredients = db.execute("SELECT DISTINCT name FROM ingredient WHERE name != '' ORDER BY name ASC").fetchall()
    all_categories = db.execute("SELECT DISTINCT name FROM category WHERE name != '' ORDER BY name ASC").fetchall()

    return render_template('recipe_form.html', 
                           recipe=recipe, 
                           ingredients=ingredients, 
                           steps_text=steps_text, 
                           category_name=category_name, 
                           image_url=image_url,
                           all_units=all_units,
                           all_ingredients=all_ingredients,
                           all_categories=all_categories)
