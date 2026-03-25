# coding: utf-8
from flask import render_template, request, redirect, url_for, flash
from database import get_db

def manage_recipe(id=None):
    db = get_db()
    recipe = None
    ingredients = []
    steps = []

    # 1. DATEN LADEN (nur bei Edit)
    if id:
        recipe = db.execute("SELECT * FROM recipe WHERE recipe_id = ?", (id,)).fetchone()
        if not recipe:
            flash("Rezept nicht gefunden!")
            return redirect(url_for('kochbuch.index'))
        
        ingredients = db.execute("""
            SELECT ri.quantity, u.name as unit, i.name as ing_name
            FROM recipe_ingredient ri
            JOIN ingredient i ON ri.ingredient_id = i.ingredient_id
            JOIN unit u ON ri.unit_id = u.unit_id
            WHERE ri.recipe_id = ? ORDER BY ri.position ASC
        """, (id,)).fetchall()
        
        steps = db.execute("SELECT instruction FROM recipe_step WHERE recipe_id = ? ORDER BY step_no ASC", (id,)).fetchall()

    # 2. FORMULAR-VERARBEITUNG (POST)
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        servings = request.form.get('servings') or 1
        
        # Prüfung auf eindeutigen Titel (nur bei Neuanlage)
        if not id:
            existing = db.execute("SELECT recipe_id FROM recipe WHERE title = ? COLLATE NOCASE", (title,)).fetchone()
            if existing:
                flash("Ein Rezept mit diesem Namen existiert bereits!")
                return render_template('recipe_form.html', recipe=request.form, ingredients=ingredients, steps=steps)

        # Transaktion starten
        if id:
            # UPDATE bestehendes Rezept
            db.execute("UPDATE recipe SET title=?, title_normalized=?, description=?, servings=? WHERE recipe_id=?",
                       (title, title.lower(), description, servings, id))
            # Verknüpfungen leeren (einfachster Weg für Update)
            db.execute("DELETE FROM recipe_ingredient WHERE recipe_id = ?", (id,))
            db.execute("DELETE FROM recipe_step WHERE recipe_id = ?", (id,))
            recipe_id = id
        else:
            # INSERT neues Rezept
            cur = db.execute("INSERT INTO recipe (title, title_normalized, description, servings) VALUES (?, ?, ?, ?)",
                             (title, title.lower(), description, servings))
            recipe_id = cur.lastrowid

        # Zutaten speichern
        qtys = request.form.getlist('qty')
        units = request.form.getlist('unit')
        names = request.form.getlist('ing_name')
        for i in range(len(names)):
            if names[i].strip():
                db.execute("INSERT OR IGNORE INTO unit (name) VALUES (?)", (units[i],))
                db.execute("INSERT OR IGNORE INTO ingredient (name) VALUES (?)", (names[i],))
                u_id = db.execute("SELECT unit_id FROM unit WHERE name=?", (units[i],)).fetchone()[0]
                i_id = db.execute("SELECT ingredient_id FROM ingredient WHERE name=?", (names[i],)).fetchone()[0]
                db.execute("INSERT INTO recipe_ingredient (recipe_id, ingredient_id, unit_id, quantity, position) VALUES (?,?,?,?,?)",
                           (recipe_id, i_id, u_id, qtys[i].replace(',', '.'), i+1))

        # Schritte speichern
        step_texts = request.form.getlist('step_text')
        for idx, text in enumerate(step_texts):
            if text.strip():
                db.execute("INSERT INTO recipe_step (recipe_id, step_no, instruction) VALUES (?, ?, ?)",
                           (recipe_id, idx + 1, text))

        db.commit()
        return redirect(url_for('kochbuch.show_details', id=recipe_id))

    return render_template('recipe_form.html', recipe=recipe, ingredients=ingredients, steps=steps)
