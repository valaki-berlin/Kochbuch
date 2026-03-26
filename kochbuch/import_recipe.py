import sqlite3
import xml.etree.ElementTree as ET
import sys
import os
from utils import normalize_title

def get_or_create_id(cursor, table, column, value):
    """Finds an ID or creates a new record if it doesn't exist."""
    cursor.execute(f"SELECT {table}_id FROM {table} WHERE {column} = ?", (value,))
    row = cursor.fetchone()
    if row:
        return row[0]
    
    # Default values for new units/ingredients/categories
    if table == 'unit':
        cursor.execute("INSERT INTO unit (name) VALUES (?)", (value,))
    else:
        cursor.execute(f"INSERT INTO {table} (name) VALUES (?)", (value,))
    return cursor.lastrowid

def parse_amount(amount_str, ingredient_name):
    """
    Validates if the amount is a number. 
    Returns 0.0 for empty strings.
    """
    if not amount_str or amount_str.strip() == "":
        amount_str = "0"
        
    cleaned = amount_str.replace(',', '.')
    try:
        return float(cleaned)
    except ValueError:
        raise ValueError(
            f"CRITICAL ERROR: Invalid amount '{amount_str}' for ingredient '{ingredient_name}'. "
            f"Please fix the XML (no calculations allowed)."
        )

def import_xml_to_db(xml_file, db_file):
    """Parses the XML and inserts data into the SQLite database."""
    if not os.path.exists(xml_file):
        print(f"Error: File '{xml_file}' not found.")
        return

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        conn = sqlite3.connect(db_file)
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()

        for recipe_node in root.iter('recipe'):
            title_node = recipe_node.find('title')
            if title_node is None: continue
            title = title_node.text
            
            # Skip duplicates
            cursor.execute("SELECT recipe_id FROM recipe WHERE title = ?", (title,))
            if cursor.fetchone():
                print(f"Skipped: '{title}' already exists.")
                continue

            print(f"Importing: {title}...")
            
            description = recipe_node.find('description').text if recipe_node.find('description') is not None else ""
            notes = recipe_node.find('notes').text.strip() if recipe_node.find('notes') is not None else ""
            
            cursor.execute("""
                INSERT INTO recipe (title, title_normalized, description, annotations, servings, is_tested)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title, normalize_title(title), description, notes, 2, 0))
            
            recipe_id = cursor.lastrowid

            # --- NEW: Process Categories ---
            categories_node = recipe_node.find('categories')
            if categories_node is not None:
                for cat_node in categories_node.findall('category'):
                    cat_name = cat_node.text.strip()
                    if cat_name:
                        # Ensure category exists and get its ID
                        cat_id = get_or_create_id(cursor, 'category', 'name', cat_name)
                        # Link recipe to category
                        cursor.execute("""
                            INSERT OR IGNORE INTO recipe_category (recipe_id, category_id)
                            VALUES (?, ?)
                        """, (recipe_id, cat_id))

            # Process Instructions
            instructions_node = recipe_node.find('instructions')
            if instructions_node is not None:
                for step in instructions_node.findall('step'):
                    cursor.execute("""
                        INSERT INTO recipe_step (recipe_id, step_no, instruction)
                        VALUES (?, ?, ?)
                    """, (recipe_id, step.get('order'), step.text))

            # Process Ingredients
            ingredients_node = recipe_node.find('ingredients')
            if ingredients_node is not None:
                for idx, ing_node in enumerate(ingredients_node.findall('ingredient'), 1):
                    ing_name = ing_node.text
                    amount = parse_amount(ing_node.get('amount', '0'), ing_name)
                    unit_name = ing_node.get('unit', 'Stück')

                    ing_id = get_or_create_id(cursor, 'ingredient', 'name', ing_name)
                    unit_id = get_or_create_id(cursor, 'unit', 'name', unit_name)

                    cursor.execute("""
                        INSERT INTO recipe_ingredient (recipe_id, ingredient_id, position, quantity, unit_id)
                        VALUES (?, ?, ?, ?, ?)
                    """, (recipe_id, ing_id, idx, amount, unit_id))

        conn.commit()
        print("Import completed successfully.")

    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        print(f"\nImport aborted:\n{e}")
    finally:
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_recipe.py <recipe.xml>")
    else:
        import_xml_to_db(sys.argv[1], 'db/RezeptDB.db')
