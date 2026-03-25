# filter.py
# Logic to build the dynamic SQL query based on search parameters
import re

def build_filter_query(search_title, search_category, search_ingredients):
    """
    Constructs a SQL query and parameter list based on provided search terms.
    Now includes the image URL from the recipe_image table.
    """
    # Updated query to include the image URL via LEFT JOIN
    query = """
        SELECT DISTINCT r.*, ri.url AS image_url 
        FROM recipe r
        LEFT JOIN recipe_image ri ON r.recipe_id = ri.recipe_id AND ri.is_primary = 1
    """
    params = []
    where_clauses = []

    # 1. Title Filter: Normalized substring search
    if search_title:
        where_clauses.append("r.title_normalized LIKE ?")
        params.append(f"%{search_title.lower()}%")

    # 2. Category Filter: Logical AND for all provided terms
    if search_category:
        # Split by comma or whitespace
        categories = re.split(r'[,\s]+', search_category)
        categories = [c for c in categories if c]
        
        for cat in categories:
            placeholder = f"cat_{len(params)}"
            query += f" JOIN recipe_category rc_{placeholder} ON r.recipe_id = rc_{placeholder}.recipe_id"
            query += f" JOIN category c_{placeholder} ON rc_{placeholder}.category_id = c_{placeholder}.category_id"
            where_clauses.append(f"c_{placeholder}.name LIKE ?")
            params.append(f"%{cat.lower()}%")

    # 3. Ingredients Filter: Logical AND for all provided terms
    if search_ingredients:
        # Split by comma or whitespace
        ingredients = re.split(r'[,\s]+', search_ingredients)
        ingredients = [i for i in ingredients if i]
        
        for ing in ingredients:
            placeholder = f"ing_{len(params)}"
            query += f" JOIN recipe_ingredient ri_{placeholder} ON r.recipe_id = ri_{placeholder}.recipe_id"
            query += f" JOIN ingredient i_{placeholder} ON ri_{placeholder}.ingredient_id = i_{placeholder}.ingredient_id"
            where_clauses.append(f"i_{placeholder}.name LIKE ?")
            params.append(f"%{ing.lower()}%")

    # Finalize the query
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    
    query += " ORDER BY r.title ASC"
    
    return query, params
