# coding: utf-8
# view_recipe.py - Zeigt Details an, löscht Rezepte und erlaubt schnelle Updates

from flask import render_template, abort, request, redirect, url_for
from database import get_db
from utils import get_complete_recipe  # Nutzt die zentrale Funktion aus utils.py 

def delete_recipe(id):
    """ Löscht ein Rezept und alle verknüpften Einträge via Cascading  """
    if request.method == 'POST':
        db = get_db()
        # Aufgrund von 'ON DELETE CASCADE' im SQL-Schema werden 
        # verknüpfte Zutaten und Schritte automatisch gelöscht. 
        db.execute("DELETE FROM recipe WHERE recipe_id = ?", (id,))
        db.commit()
    return redirect(url_for('kochbuch.index'))

def update_fast(id):
    """ Speichert Notizen direkt aus der Detailansicht  """
    if request.method == 'POST':
        db = get_db()
        notes = request.form.get('notes') # Formularfeld 'notes' -> DB-Spalte 'annotations' 
        
        db.execute("UPDATE recipe SET annotations = ? WHERE recipe_id = ?", 
                   (notes, id))
        db.commit()
    return redirect(url_for('kochbuch.show_details', id=id))


def show_details(id):
    db = get_db()
    # Fetch all data using the centralized utility function [cite: 1, 7]
    recipe_data = get_complete_recipe(db, id)
    
    if recipe_data is None:
        abort(404)

    # Map ingredients to match the variable names used in recipe_detail.html [cite: 7, 8]
    formatted_ingredients = []
    for ing in recipe_data.get('ingredients', []):
        name = ing.get('ingredient_name') or ""
        # Check if the name ends with a colon to mark it as a sub-heading
        is_header = name.strip().endswith(':')
        formatted_ingredients.append({
            'quantity': ing.get('quantity'),
            'unit': ing.get('unit_name'),
            'ing_name': name,
            'preparation_note': ing.get('preparation_note'),
            'is_optional': ing.get('is_optional'),
            'is_header': is_header  # New flag for the template
        })
        
    # Convert steps into a list of dictionaries so 'step.instruction' works in the template [cite: 6, 8]
    formatted_steps = [{'instruction': s} for s in recipe_data.get('steps', [])]

    # Map categories into objects with a 'name' attribute for the template badges [cite: 7, 8]
    formatted_categories = [{'name': cat} for cat in recipe_data.get('categories', [])]

    return render_template('recipe_detail.html', 
                           recipe=recipe_data, 
                           ingredients=formatted_ingredients, 
                           steps=formatted_steps, 
                           categories=formatted_categories)

