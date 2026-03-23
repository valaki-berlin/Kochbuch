import sqlite3
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os

def prettify(elem):
    """Gibt das XML mit Einrückungen (Indentation) zurück."""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="    ")

def export_database_to_xml(db_file, output_dir="export"):
    # Ordner erstellen, falls nicht vorhanden
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row  # Erlaubt Zugriff via Spaltennamen
    cursor = conn.cursor()

    # 1. Alle Rezepte holen
    cursor.execute("SELECT * FROM recipe")
    recipes = cursor.fetchall()

    for r in recipes:
        recipe_id = r['recipe_id']
        title_norm = r['title_normalized']
        
        # XML Wurzel-Element für dieses Rezept
        root = ET.Element("cookbook")
        recipe_node = ET.SubElement(root, "recipe", id=str(recipe_id))
        
        # Metadaten
        ET.SubElement(recipe_node, "title").text = r['title']
        ET.SubElement(recipe_node, "description").text = r['description']
        
        # 2. Zutaten holen
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
            # Da quantity REAL ist, formatieren wir .0 weg, falls nicht nötig
            qty = f"{ing['quantity']:g}".replace('.', ',')
            ing_elem = ET.SubElement(ingredients_node, "ingredient", 
                                     amount=qty, 
                                     unit=ing['unit_name'])
            ing_elem.text = ing['ing_name']

        # 3. Anweisungen (Steps) holen
        steps_node = ET.SubElement(recipe_node, "instructions")
        cursor.execute("SELECT step_no, instruction FROM recipe_step WHERE recipe_id = ? ORDER BY step_no", (recipe_id,))
        
        for step in cursor.fetchall():
            step_elem = ET.SubElement(steps_node, "step", order=str(step['step_no']))
            step_elem.text = step['instruction']

        # 4. Notizen (Annotations)
        if r['annotations']:
            ET.SubElement(recipe_node, "notes").text = r['annotations']

        # Speichern der Datei
        file_path = os.path.join(output_dir, f"{title_norm}.xml")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(prettify(root))
        
        print(f"Exportiert: {file_path}")

    conn.close()
    print(f"\nFertig! Alle Rezepte wurden in den Ordner '{output_dir}' exportiert.")

if __name__ == "__main__":
    export_database_to_xml('../rezepte/RezeptDB.db')
