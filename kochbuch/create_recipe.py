# coding: utf-8
# create_recipe.py - Logic for adding new recipes

import re  
from flask import render_template, request, redirect, url_for, flash
from database import get_db

def normalize_german_text(text):
    """ 
    Standardized normalization: lowercase, replaces umlauts, 
    removes special chars, and collapses all whitespace/dashes into a single dash.
    """
    if not title: return ""
    # 1. Lowercase and strip whitespace
    res = title.lower().strip()
    # 2. Replace German umlauts
    res = res.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss').replace('&', 'und')
    # 3. Remove everything except alphanumeric, spaces, and dashes
    res = re.sub(r'[^a-z0-9\s-]', '', res)
    # 4. Replace one or more spaces/dashes with a single dash
    res = re.sub(r'[\s-]+', '-', res)
    return res.strip('-')

def show_form():
    if request.method == 'POST':
        db = get_db()
        
        # 1. Collect main recipe data from form fields
        title = request.form.get('title')
        categories_raw = request.form.get('categories', '')
        servings = request.form.get('servings', 2)
        is_tested = 1 if request.form.get('is_tested') == 'true' else 0
        source = request.form.get('source', '')
        instructions_raw = request.form.get('instructions', '')
        notes = request.form.get('notes', '') # Maps to 'annotations' column

        if not title:
            return "Title is required", 400

        try:
            # 2. Insert into 'recipe' table
            sql_recipe = """
                INSERT INTO recipe (title, title_normalized, original_source, annotations, servings, is_tested)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            cursor = db.execute(sql_recipe, (
                title, normalize_german_text(title), source, notes, servings, is_tested
            ))
            recipe_id = cursor.lastrowid

            # 3. Process Categories (Splitting by COMMA as requested)
            # --- Section 3 in create_recipe.py ---

            # Get the raw string from the form
            categories_raw = request.form.get('category', '')

            # Use a regular expression to split by comma OR any whitespace (space, tab, newline)
            # The pattern r'[,\s]+' matches one or more commas or spaces
            cat_names = re.split(r'[,\s]+', categories_raw)

            # Clean the list: strip extra whitespace and ignore empty strings
            cat_list = [c.strip() for c in cat_names if c.strip()]

            for cat_name in cat_list:
                # Insert the individual category into the master 'category' table
                db.execute("INSERT OR IGNORE INTO category (name) VALUES (?)", (cat_name,))
    
                # Get the ID for the clean, single category name
                cat_res = db.execute("SELECT category_id FROM category WHERE name = ?", (cat_name,)).fetchone()
    
                # Link the recipe to this specific category ID
                if cat_res:
                    db.execute("INSERT OR IGNORE INTO recipe_category (recipe_id, category_id) VALUES (?, ?)", 
                               (recipe_id, cat_res[0]))


            # 4. Process Instructions (Splitting by empty lines)
            # Use .replace('\r\n', '\n') to handle different OS line endings before splitting
            normalized_instr = instructions_raw.replace('\r\n', '\n')
            # Split by double newline to detect actual empty lines
            steps = [s.strip() for s in normalized_instr.split('\n\n') if s.strip()]
            
            for idx, step_text in enumerate(steps, start=1):
                # Using 'recipe_step' and 'step_no' as per SQL schema
                db.execute("INSERT INTO recipe_step (recipe_id, step_no, instruction) VALUES (?, ?, ?)",
                           (recipe_id, idx, step_text))

            # 5. Process Ingredients (recipe_ingredient table)
            amounts = request.form.getlist('amount[]')
            units = request.form.getlist('unit[]')
            ingredients = request.form.getlist('ingredient[]')

            for i in range(len(ingredients)):
                ing_name = ingredients[i].strip()
                if ing_name:
                    # Ingredient master
                    db.execute("INSERT OR IGNORE INTO ingredient (name) VALUES (?)", (ing_name,))
                    ing_id = db.execute("SELECT ingredient_id FROM ingredient WHERE name = ?", (ing_name,)).fetchone()[0]
                    
                    # Unit handling: Look up unit_id
                    unit_name = units[i].strip() or 'Stück'
                    unit_res = db.execute("SELECT unit_id FROM unit WHERE name = ? COLLATE NOCASE", (unit_name,)).fetchone()
                    # Fallback to unit_id 1 if not found
                    unit_id = unit_res[0] if unit_res else 1 

                    # Link with quantity
                    db.execute("""
                        INSERT INTO recipe_ingredient (recipe_id, ingredient_id, position, quantity, unit_id)
                        VALUES (?, ?, ?, ?, ?)
                    """, (recipe_id, ing_id, i+1, amounts[i] or 1, unit_id))

            db.commit()
            return redirect(url_for('kochbuch.show_details', id=recipe_id))

        except Exception as e:
            db.rollback()
            return f"Database Error: {str(e)}", 500

    return render_template('recipe_form.html')
