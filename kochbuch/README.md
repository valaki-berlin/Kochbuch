### Basic structure of the database design:

### Core Content Tables
* **`recipe`**: The central table storing primary recipe data, such as titles, descriptions, and cooking times. It uses `COLLATE NOCASE` for case-insensitive searching and includes a `title_normalized` column for optimized German character searches.
* **`recipe_step`**: Stores the ordered instructions for each recipe, linked via a foreign key.
* **`ingredient`**: A master list of unique ingredient names.
* **`unit`**: Defines measurement units (e.g., grams, liters) and includes a `factor_to_base` for simple unit conversions.
* **`recipe_ingredient`**: A junction table linking recipes to ingredients, specifying the required quantity and unit for each.

### Organization & Metadata
* **`category` & `recipe_category`**: Used for assigning recipes to flat categories like "Pasta" or "Italian".
* **`category_relation`**: A specialized table that allows for flexible hierarchies, such as defining "Italian" as a broader category than "Pasta".
* **`tag` & `recipe_tag`**: Provides optional, free-form keyword tagging for recipes.
* **`recipe_image`**: Manages image URLs, using a partial unique index to ensure only one image is marked as "primary" per recipe.

### System & Search
* **`schema_info`**: Tracks the version of the database schema for future updates.
* **`recipe_fts`**: A virtual table utilizing **FTS5** (Full-Text Search) to allow high-performance searching across recipe titles and descriptions. Triggers are included to keep this index synchronized with the main `recipe` table.
