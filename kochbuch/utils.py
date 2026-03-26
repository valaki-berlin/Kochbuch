# coding: utf-8
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom

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
    res = res.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
    
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
    """Get all categories of a recipe and concatenate a resulting string."""
    rows = db.execute("""
        SELECT c.name FROM category c 
        JOIN recipe_category rc ON c.category_id = rc.category_id 
        WHERE rc.recipe_id = ? ORDER BY c.name ASC""", (recipe_id,)).fetchall()
    return ", ".join([row['name'] for row in rows])

def save_recipe_categories(db, recipe_id, category_string):
    """Delete all previous category relations and establish new ones."""
    # Bestehende Verknüpfungen entfernen
    db.execute("DELETE FROM recipe_category WHERE recipe_id = ?", (recipe_id,))
    
    if not category_string:
        return

    # Split string
    categories = [c.strip() for c in re.split(r'[,\s;]+', category_string) if c.strip()]
    
    for cat in categories:
        # Kategorie in Stammdaten sicherstellen
        db.execute("INSERT OR IGNORE INTO category (name) VALUES (?)", (cat,))
        
        # ID holen
        cat_row = db.execute("SELECT category_id FROM category WHERE name=?", (cat,)).fetchone()
        if cat_row:
            cid = cat_row[0]
            # Verknüpfung erstellen
            db.execute("INSERT INTO recipe_category (recipe_id, category_id) VALUES (?,?)", 
                       (recipe_id, cid))

