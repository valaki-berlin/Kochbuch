# coding: utf-8
import re
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from PIL import Image

def handle_image_upload(recipe_id, db, request_files, upload_folder, target_width=600):
    """
    Saves image to disk and updates the recipe_image relation table.
    """
    if 'image_file' not in request_files:
        return None
    
    file = request_files['image_file']
    if file and file.filename != '':
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
            return None
            
        filename = f"recipe_{recipe_id}{ext}"
        filepath = os.path.join(upload_folder, filename)

        try:
            img = Image.open(file)
            w_percent = (target_width / float(img.size[0]))
            h_size = int((float(img.size[1]) * float(w_percent)))
            img = img.resize((target_width, h_size), Image.Resampling.LANCZOS)
            img.save(filepath)
            
            # Use the dedicated recipe_image table as per schema
            db.execute("""
                INSERT OR REPLACE INTO recipe_image (recipe_id, url, is_primary)
                VALUES (?, ?, 1)
            """, (recipe_id, filename))
        except Exception as e:
            print(f"Image upload error: {e}")

def normalize_title(title):
    """ 
    Standardized normalization for URLs and duplicate checks.
    1. Lowercase & strip
    2. Replaces German umlauts (ae, oe, ue, ss)
    3. Removes all special characters except letters and numbers
    4. Collapses multiple spaces/dashes into a single dash
    """
    if not title:
        return ""
    
    # Lowercase and handle German specific characters
    res = title.lower().strip()
    res = res.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss').replace(' ', '-')
    
    # Remove everything except a-z, 0-9, spaces, and dashes
    res = re.sub(r'[^a-z0-9\s-]', '', res)
    
    # Replace any sequence of whitespace or dashes with one single dash
    res = re.sub(r'[\s-]+', '-', res)
    
    return res.strip('-')

def prettify_xml(elem):
    """
    Returns a pretty-printed XML string for the ElementTree.
    Used during export to keep XML files human-readable.
    """
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="    ")

def get_categories_string(db, recipe_id):
    """Get all categories of a recipe and concatenate into a comma-separated string."""
    rows = db.execute("""
        SELECT c.name FROM category c 
        JOIN recipe_category rc ON c.category_id = rc.category_id 
        WHERE rc.recipe_id = ? ORDER BY c.name ASC""", (recipe_id,)).fetchall()
    return ", ".join([row['name'] for row in rows])


###  read recipe from database, used by anyone

def get_complete_recipe(db, recipe_id):
    """
    Fetches all data for a specific recipe from the database.
    Returns a dictionary containing base data, categories, ingredients, and steps.
    Used by edit_recipe, export_recipes, and for detail views.
    """
    # 1. Fetch base recipe data
    recipe = db.execute("""
        SELECT r.recipe_id, r.title, r.title_normalized, r.original_source, 
               r.annotations, r.servings, r.is_tested, r.description,
               ri.url AS image_url
        FROM recipe r
        LEFT JOIN recipe_image ri ON r.recipe_id = ri.recipe_id AND ri.is_primary = 1
        WHERE r.recipe_id = ?
    """, (recipe_id,)).fetchone()
    if not recipe:
        return None

    # Convert sqlite3.Row to a real dictionary to make it mutable/serializable
    recipe_data = dict(recipe)

    # 2. Fetch categories as a list of names
    categories = db.execute("""
        SELECT name FROM category c
        JOIN recipe_category rc ON c.category_id = rc.category_id
        WHERE rc.recipe_id = ? ORDER BY name ASC
    """, (recipe_id,)).fetchall()
    recipe_data['categories'] = [c['name'] for c in categories]
    # Also provide as a single string for the form input field
    recipe_data['categories_string'] = ", ".join(recipe_data['categories'])

    # 3. Fetch ingredients with units, notes and optional flag
    ingredients = db.execute("""
        SELECT ri.quantity, u.name as unit_name, i.name as ingredient_name, 
               ri.preparation_note, ri.is_optional
        FROM recipe_ingredient ri
        JOIN unit u ON ri.unit_id = u.unit_id
        JOIN ingredient i ON ri.ingredient_id = i.ingredient_id
        WHERE ri.recipe_id = ?
        ORDER BY ri.position
    """, (recipe_id,)).fetchall()
    recipe_data['ingredients'] = [dict(ing) for ing in ingredients]

    # 4. Fetch instructions (steps)
    steps = db.execute("""
        SELECT instruction FROM recipe_step 
        WHERE recipe_id = ? 
        ORDER BY step_no
    """, (recipe_id,)).fetchall()
    recipe_data['steps'] = [s['instruction'] for s in steps]
    # Provide as a single text block with double newlines for the textarea in the form
    recipe_data['steps_text'] = "\n\n".join(recipe_data['steps'])

    return recipe_data

###  write recipe to database, used by anyone

def save_recipe_categories(db, recipe_id, category_string):
    """Delete all previous category relations and establish new ones based on input string."""
    # Remove existing links
    db.execute("DELETE FROM recipe_category WHERE recipe_id = ?", (recipe_id,))
    
    if not category_string:
        return

    # Split string by comma, space or semicolon
    categories = [c.strip() for c in re.split(r'[,\s;]+', category_string) if c.strip()]
    
    for cat in categories:
        # Ensure category exists in master data
        db.execute("INSERT OR IGNORE INTO category (name) VALUES (?)", (cat,))
        
        # Get ID
        cat_row = db.execute("SELECT category_id FROM category WHERE name=?", (cat,)).fetchone()
        if cat_row:
            cid = cat_row[0]
            # Create link
            db.execute("INSERT INTO recipe_category (recipe_id, category_id) VALUES (?,?)", 
                       (recipe_id, cid))

def save_complete_recipe(db, recipe_id, form_data):
    """
    Main orchestrator to save all parts of a recipe.
    Delegates to specialized sub-functions.
    """
    # 1. Update basic fields (title, servings, etc.)
    update_recipe_base_data(db, recipe_id, form_data)
    
    # 2. Update categories
    save_recipe_categories(db, recipe_id, form_data.get('category', ''))
    
    # 3. Update ingredients (including notes and optional flag)
    save_recipe_ingredients(
        db, recipe_id,
        form_data.getlist('ingredient_amount'),
        form_data.getlist('ingredient_unit'),
        form_data.getlist('ingredient_name'),
        form_data.getlist('ingredient_note'),
        form_data.getlist('ingredient_optional')
    )
    
    # 4. Update instructions
    save_recipe_steps(db, recipe_id, form_data.get('steps_text', ''))

def update_recipe_base_data(db, recipe_id, form_data):
    """Updates core recipe attributes in the database."""
    title = form_data.get('title', 'Untitled Recipe')
    title_norm = normalize_title(title)
    servings = form_data.get('servings', 2)
    # Checkbox logic: handle multiple possible "true" values
    is_tested = 1 if form_data.get('is_tested') in ['on', 'true', '1'] else 0
    annotations = form_data.get('notes', '') 
    source = form_data.get('source', '')

    db.execute("""
        UPDATE recipe 
        SET title=?, title_normalized=?, servings=?, is_tested=?, annotations=?, original_source=?
        WHERE recipe_id=?
    """, (title, title_norm, servings, is_tested, annotations, source, recipe_id))

def save_recipe_ingredients(db, recipe_id, amounts, units, names, notes, optionals):
    """Processes ingredient list and manages master data for units and names."""
    # Clear existing ingredients
    db.execute("DELETE FROM recipe_ingredient WHERE recipe_id = ?", (recipe_id,))
    
    # Iterate through lists (using zip to keep them synchronized)
    for i, (amt, unt, nm, nt, opt) in enumerate(zip(amounts, units, names, notes, optionals), start=1):
        clean_nm = nm.strip()
        if not clean_nm:
            continue
            
        # Ensure unit exists
        clean_unt = unt.strip() or ''
        db.execute("INSERT OR IGNORE INTO unit (name) VALUES (?)", (clean_unt,))
        u_id = db.execute("SELECT unit_id FROM unit WHERE name=?", (clean_unt,)).fetchone()[0]
        
        # Ensure ingredient master record exists
        db.execute("INSERT OR IGNORE INTO ingredient (name) VALUES (?)", (clean_nm,))
        i_id = db.execute("SELECT ingredient_id FROM ingredient WHERE name=?", (clean_nm,)).fetchone()[0]
        
        # Insert link with position and new extended attributes
        db.execute("""
            INSERT INTO recipe_ingredient 
            (recipe_id, ingredient_id, unit_id, quantity, position, preparation_note, is_optional)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (recipe_id, i_id, u_id, amt.replace(',', '.') if amt else 0, i, nt, int(opt)if (opt and str(opt).isdigit()) else 0 ))

def save_recipe_steps(db, recipe_id, steps_raw):
    """Splits instruction text block by empty lines and saves individual steps."""
    # Clear existing steps
    db.execute("DELETE FROM recipe_step WHERE recipe_id = ?", (recipe_id,))
    
    # Split by empty lines (double newline)
    processed_steps = re.split(r'\n\s*\n', steps_raw.strip())
    
    step_counter = 1
    for block in processed_steps:
        clean_block = block.strip()
        if clean_block:
            db.execute("""
                INSERT INTO recipe_step (recipe_id, step_no, instruction) 
                VALUES (?, ?, ?)
            """, (recipe_id, step_counter, clean_block))
            step_counter += 1

