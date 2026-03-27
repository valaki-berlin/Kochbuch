import sqlite3
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os
import re

def prettify(elem):
    """Returns an XML string with indentation for better readability."""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="    ")

def export_database_to_xml(db_file, output_dir="export"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM recipe")
    recipes = cursor.fetchall()

    for r in recipes:
        recipe_id = r['recipe_id']
        title_norm = r['title_normalized']
        
        root = ET.Element("cookbook")
        recipe_node = ET.SubElement(root, "recipe", id=str(recipe_id))
        
        ET.SubElement(recipe_node, "title").text = r['title']
        ET.SubElement(recipe_node, "description").text = r['description']
        
        # --- Ingredients ---
        ingredients_node = ET.SubElement(recipe_node, "ingredients")
        cursor.execute("""
            SELECT ri.quantity, u.name as unit_name, i.name as ing_name
            FROM recipe_ingredient ri
            JOIN ingredient i ON ri.ingredient_id = i.ingredient_id
            JOIN unit u ON ri.unit_id = u.unit_id
            WHERE ri.recipe_id = ?
            ORDER BY ri.position
        """, (recipe_id,))
        
        for ing in cursor.fetchall():

            raw_qty = ing['quantity']
            if raw_qty == 0:
                qty_str = ""
            else:
                qty_str = f"{raw_qty:g}".replace('.', ',')
            ing_elem = ET.SubElement(ingredients_node, "ingredient", 
                                     amount=qty_str, 
                                     unit=ing['unit_name'])
            ing_elem.text = ing['ing_name']

        # --- UPDATED: Categories (Only export if they exist) ---
        cursor.execute("""
            SELECT c.name 
            FROM recipe_category rc
            JOIN category c ON rc.category_id = c.category_id
            WHERE rc.recipe_id = ?
        """, (recipe_id,))
        
        all_category_rows = cursor.fetchall()
        
        # Check if there are any categories before creating the parent tag
        if all_category_rows:
            categories_node = ET.SubElement(recipe_node, "categories")
            for cat_row in all_category_rows:
                # Split by comma in case of legacy "broken" data
                raw_names = re.split(r'[,]+', cat_row['name'])
                for name in raw_names:
                    clean_name = name.strip()
                    if clean_name:
                        cat_elem = ET.SubElement(categories_node, "category")
                        cat_elem.text = clean_name

        # --- Instructions ---
        steps_node = ET.SubElement(recipe_node, "instructions")
        cursor.execute("SELECT step_no, instruction FROM recipe_step WHERE recipe_id = ? ORDER BY step_no", (recipe_id,))
        
        for step in cursor.fetchall():
            step_elem = ET.SubElement(steps_node, "step", order=str(step['step_no']))
            step_elem.text = step['instruction']

        if r['annotations']:
            ET.SubElement(recipe_node, "notes").text = r['annotations']

        # Save the file
        file_path = os.path.join(output_dir, f"{title_norm}.xml")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(prettify(root))
        
        print(f"Exported: {file_path}")

    conn.close()
    print(f"\nDone! Exported to '{output_dir}'.")

if __name__ == "__main__":
    # Adjust path if your DB is in a different location
    export_database_to_xml('../db/RezeptDB.db')
