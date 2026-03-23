# coding: utf-8
# create_recipe.py - Logic for adding new recipes

from flask import render_template, request, redirect, url_for, g, flash
from database import get_db  # <--- Hier importieren!

def normalize_german_text(text):
    """
    Simple normalization for German umlauts to improve searchability.
    Example: 'Süßkartoffel-Suppe' -> 'suesskartoffel-suppe'
    """
    if not text:
        return ""
    res = text.lower()
    res = res.replace(u'ä', 'ae').replace(u'ö', 'oe').replace(u'ü', 'ue').replace(u'ß', 'ss')
    # Replace spaces with hyphens for a clean search string
    res = res.replace(' ', '-')
    return res

def show_form():
    if request.method == 'POST':
        # Get data from form
        title = request.form.get('title')
        description = request.form.get('description')
        servings = request.form.get('servings', 2)
        prep_time = request.form.get('prep_minutes', 0)
        cook_time = request.form.get('cook_minutes', 0)
        
        # Validation
        if not title:
            return "Title is required", 400
            
        # Prepare normalized title for the database
        title_norm = normalize_german_text(title)
        
        db = get_db()   
        try:
            sql = """
                INSERT INTO recipe (title, title_normalized, description, servings, prep_minutes, cook_minutes)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            cursor = db.execute(sql, (title, title_norm, description, servings, prep_time, cook_time))
            db.commit()
            
            # Redirect to the newly created recipe
            return redirect(url_for('kochbuch.show_details', id=cursor.lastrowid))
        except Exception as e:
            db.rollback()
            return f"Database Error: {str(e)}", 500

    # If GET, just show the empty form
    return render_template('recipe_form.html')
