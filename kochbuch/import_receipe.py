import sqlite3
import xml.etree.ElementTree as ET
import sys
import os

def normalize_title(title):
    """Normalisiert den Titel für die Suche und die Spalte title_normalized."""
    substitutions = {
        'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss',
        ' ': '-', '.': '', ',': ''
    }
    res = title.lower()
    for char, repl in substitutions.items():
        res = res.replace(char, repl)
    return res

def get_or_create_id(cursor, table, column, value):
    """Sucht eine ID oder legt einen neuen Datensatz an."""
    cursor.execute(f"SELECT {table}_id FROM {table} WHERE {column} = ?", (value,))
    row = cursor.fetchone()
    if row:
        return row[0]
    
    # Standard-Werte für neue Einheiten/Zutaten
    if table == 'unit':
        cursor.execute("INSERT INTO unit (name, group_code) VALUES (?, 'unknown')", (value,))
    else:
        cursor.execute(f"INSERT INTO {table} (name) VALUES (?)", (value,))
    return cursor.lastrowid

def parse_amount(amount_str, ingredient_name):
    """
    Prüft, ob die Menge eine reine Zahl ist. 
    Wirft einen ValueError bei ungültigen Formaten wie '500+250'.
    """
    cleaned = amount_str.replace(',', '.')
    try:
        return float(cleaned)
    except ValueError:
        raise ValueError(
            f"KRITISCHER FEHLER: Ungültige Mengenangabe '{amount_str}' bei Zutat '{ingredient_name}'. "
            f"Bitte das XML korrigieren (keine Rechnungen oder Sonderzeichen erlaubt)."
        )

def import_xml_to_db(xml_file, db_file):
    if not os.path.exists(xml_file):
        print(f"Fehler: Die Datei '{xml_file}' wurde nicht gefunden.")
        return

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        conn = sqlite3.connect(db_file)
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()

        for recipe_node in root.findall('recipe'):
            title = recipe_node.find('title').text
            
            # Dubletten-Check
            cursor.execute("SELECT recipe_id FROM recipe WHERE title = ?", (title,))
            if cursor.fetchone():
                print(f"Übersprungen: '{title}' ist bereits in der Datenbank.")
                continue

            print(f"Importiere: {title}...")
            
            description = recipe_node.find('description').text if recipe_node.find('description') is not None else ""
            notes = recipe_node.find('notes').text.strip() if recipe_node.find('notes') is not None else ""
            
            # Rezept-Basisdaten
            cursor.execute("""
                INSERT INTO recipe (title, title_normalized, description, annotations, servings, is_tested)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (title, normalize_title(title), description, notes, 1))
            
            recipe_id = cursor.lastrowid

            # Schritte
            for step in recipe_node.find('instructions').findall('step'):
                cursor.execute("""
                    INSERT INTO recipe_step (recipe_id, step_no, instruction)
                    VALUES (?, ?, ?)
                """, (recipe_id, step.get('order'), step.text))

            # Zutaten mit Validierung
            for idx, ing_node in enumerate(recipe_node.find('ingredients').findall('ingredient'), 1):
                ing_name = ing_node.text
                amount_raw = ing_node.get('amount', '0')
                unit_name = ing_node.get('unit', 'Stück')

                # Hier erfolgt der Abbruch bei "500+250"
                amount = parse_amount(amount_raw, ing_name)

                ing_id = get_or_create_id(cursor, 'ingredient', 'name', ing_name)
                unit_id = get_or_create_id(cursor, 'unit', 'name', unit_name)

                cursor.execute("""
                    INSERT INTO recipe_ingredient (recipe_id, ingredient_id, position, quantity, unit_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (recipe_id, ing_id, idx, amount, unit_id))

        conn.commit()
        print("Import erfolgreich abgeschlossen.")

    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        print(f"\nAbbruch während des Imports:\n{e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    # Parameter-Check: python script.py DATEINAME
    if len(sys.argv) < 2:
        print("Usage: python import_recipe.py <recipe.xml>")
    else:
        target_xml = sys.argv[1]
        import_xml_to_db(target_xml, 'rezepte/RezeptDB.db')
