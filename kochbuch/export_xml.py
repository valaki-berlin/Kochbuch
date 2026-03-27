import sqlite3
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os

def prettify(elem):
    """Returns a pretty-printed XML string for better readability."""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="    ")

def export_database_to_xml(db_file, output_dir="export"):
    """Exports all recipes from the SQLite database to individual XML files."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Fetch all recipes from the core table
    cursor.execute("SELECT * FROM recipe")
    recipes = cursor.fetchall()

    for r in recipes:
        recipe_id = r['recipe_id']
        title_norm = r['title_normalized']
        
        # Create the XML root structure
        root = ET.Element("cookbook")
        recipe_node = ET.SubElement(root, "recipe")
        
        ET.SubElement(recipe_node, "title").text = r['title']
        ET.SubElement(recipe_node, "description").text = r['description']
        
        # --- Process Categories ---
        cursor.execute("""
            SELECT c.name 
            FROM recipe_category rc
            JOIN category c ON rc.category_id = c.category_id
            WHERE rc.recipe_id = ?
        """, (recipe_id,))
        
        all_category_rows = cursor.fetchall()
        if all_category_rows:
            categories_node = ET.SubElement(recipe_node, "categories")
            for cat_row in all_category_rows:
                cat_elem = ET.SubElement(categories_node, "category")
                cat_elem.text = cat_row['name'].strip()

        # --- Process Ingredients (with extended attributes) ---
        ingredients_node = ET.SubElement(recipe_node, "ingredients")
        cursor.execute("""
            SELECT ri.quantity, u.name as unit_name, i.name as ing_name, 
                   ri.preparation_note, ri.is_optional
            FROM recipe_ingredient ri
            JOIN ingredient i ON ri.ingredient_id = i.ingredient_id
            JOIN unit u ON ri.unit_id = u.unit_id
            WHERE ri.recipe_id = ?
            ORDER BY ri.position
        """, (recipe_id,))
        
        for ing in cursor.fetchall():
            # Ensure quantity is a numeric type to avoid TypeError during comparison
            try:
                raw_qty = float(ing['quantity'])
            except (ValueError, TypeError):
                raw_qty = 0.0
            
            # Format amount: replace dot with comma for XML compatibility, default to '0'
            qty_str = f"{raw_qty:g}".replace('.', ',') if raw_qty > 0 else "0"
            
            # Convert internal boolean-integer (0/1) back to XML string (NO/YES)
            opt_str = "YES" if ing['is_optional'] == 1 else "NO"

            # Create ingredient element with attributes
            ing_elem = ET.SubElement(ingredients_node, "ingredient", 
                                     amount=qty_str, 
                                     unit=ing['unit_name'],
                                     ingredient=ing['ing_name'],
                                     Optional=opt_str)
            
            # Add preparation note attribute if it exists in the database
            if ing['preparation_note']:
                ing_elem.set('note', ing['preparation_note'])

        # --- Process Instructions ---
        steps_node = ET.SubElement(recipe_node, "instructions")
        cursor.execute("""
            SELECT step_no, instruction 
            FROM recipe_step 
            WHERE recipe_id = ? 
            ORDER BY step_no
        """, (recipe_id,))
        
        for step in cursor.fetchall():
            step_elem = ET.SubElement(steps_node, "step", order=str(step['step_no']))
            step_elem.text = step['instruction']

        # --- Process Annotations/Notes ---
        if r['annotations']:
            ET.SubElement(recipe_node, "notes").text = r['annotations']

        # Save the generated XML to a file named after the normalized title
        file_path = os.path.join(output_dir, f"{title_norm}.xml")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(prettify(root))
        
        print(f"Exported: {file_path}")

    conn.close()
    print(f"\nExport complete. Files are located in the '{output_dir}' directory.")

if __name__ == "__main__":
    # Specify the path to your SQLite database
    export_database_to_xml('db/RezeptDB.db')
