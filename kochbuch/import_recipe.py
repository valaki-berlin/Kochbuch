import sqlite3
import xml.etree.ElementTree as ET
import sys
import os

def normalize_title(title):
    """Normalizes the title for search and the title_normalized column."""
    substitutions = {
        'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss',
        ' ': '-', '.': '', ',': ''
    }
    res = title.lower()
    for char, repl in substitutions.items():
        res = res.replace(char, repl)
    return res

def get_or_create_id(cursor, table, column, value):
    """Finds an ID or creates a new record if it doesn't exist."""
    cursor.execute(f"SELECT {table}_id FROM {table} WHERE {column} = ?", (value,))
    row = cursor.fetchone()
    if row:
        return row[0]
    
    # Default values for new units/ingredients
    if table == 'unit':
        cursor.execute("INSERT INTO unit (name) VALUES (?)", (value,))
    else:
        cursor.execute(f"INSERT INTO {table} (name) VALUES (?)", (value,))
    return cursor.lastrowid

def parse_amount(amount_str, ingredient_name):
    """
    Validates if the amount is a number. 
    Returns 0.0 for empty strings.
    Raises ValueError for invalid formats like '500+250'.
    """
    if not amount_str or amount_str.strip() == "":
        amount_str = "0"
        
    cleaned = amount_str.replace(',', '.')
    try:
        return float(cleaned)
    except ValueError:
        raise ValueError(
            f"CRITICAL ERROR: Invalid amount '{amount_str}' for ingredient '{ingredient_name}'. "
            f"Please fix the XML (no calculations or special characters allowed)."
        )

def import_xml_to_db(xml_file, db_file):
    """Parses the XML and inserts data into the SQLite database."""
    if not os.path.exists(xml_file):
        print(f"Error: File '{xml_file}' not found.")
        return

    print(f"DEBUG: Using database at: {os.path.abspath(db_file)}")

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        recipes = list(root.iter('recipe'))
        print(f"DEBUG: I found {len(recipes)} recipe(s) in the XML file.")
        
        conn = sqlite3.connect(db_file)
        # Enable foreign key support
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()

        # Iterate through all recipes in the XML
#        for recipe_node in root.findall('recipe'):
        for recipe_node in root.iter('recipe'):
            title_element = recipe_node.find('title')

            print(f"DEBUG: Attempting to import '{title_element.text}'")
            print(f"DEBUG: Found recipe in XML: {title_element}")
            if title_element is None:
                continue
            title = title_element.text
            
            # Check for duplicates by title
            cursor.execute("SELECT recipe_id FROM recipe WHERE title = ?", (title,))
            if cursor.fetchone():
                print(f"Skipped: '{title}' already exists in database.")
                continue

            print(f"Importing: {title}...")
            
            description = recipe_node.find('description').text if recipe_node.find('description') is not None else ""
            notes = recipe_node.find('notes').text.strip() if recipe_node.find('notes') is not None else ""
            
            # Insert recipe with default values: servings=2, is_tested=0
            cursor.execute("""
                INSERT INTO recipe (title, title_normalized, description, annotations, servings, is_tested)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title, normalize_title(title), description, notes, 2, 0))
            
            recipe_id = cursor.lastrowid

            # Insert steps from instructions
            instructions_node = recipe_node.find('instructions')
            if instructions_node is not None:
                for step in instructions_node.findall('step'):
                    cursor.execute("""
                        INSERT INTO recipe_step (recipe_id, step_no, instruction)
                        VALUES (?, ?, ?)
                    """, (recipe_id, step.get('order'), step.text))

            # Insert ingredients with amount validation
            ingredients_node = recipe_node.find('ingredients')
            if ingredients_node is not None:
                for idx, ing_node in enumerate(ingredients_node.findall('ingredient'), 1):
                    ing_name = ing_node.text
                    amount_raw = ing_node.get('amount', '0')
                    unit_name = ing_node.get('unit', 'Stück')

                    # Parse amount (handles empty strings as 0.0)
                    amount = parse_amount(amount_raw, ing_name)

                    ing_id = get_or_create_id(cursor, 'ingredient', 'name', ing_name)
                    unit_id = get_or_create_id(cursor, 'unit', 'name', unit_name)

                    cursor.execute("""
                        INSERT INTO recipe_ingredient (recipe_id, ingredient_id, position, quantity, unit_id)
                        VALUES (?, ?, ?, ?, ?)
                    """, (recipe_id, ing_id, idx, amount, unit_id))

        conn.commit()
        print("Import completed successfully.")

    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        print(f"\nImport aborted:\n{e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    # CLI usage: python import_recipe.py <file.xml>
    if len(sys.argv) < 2:
        print("Usage: python import_recipe.py <recipe.xml>")
    else:
        target_xml = sys.argv[1]
        rint(f"DEBUG: Attempting to import '{target_xml}'") 
        # Default database path for CLI execution
        import_xml_to_db(target_xml, 'rezepte/RezeptDB.db')
