## Basic structure of the database design:

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


## Basic structure of main code segments

### `main.py`
The central Flask application entry point that manages routing and global configurations.
* **`inject_globals()`**: Injects the translation helper function `t()` into all HTML templates.
* **`inject_translations()`**: Provides a dictionary of localized strings to the template context.
* **`get_string(key)`**: Retrieves a translated string based on the provided key from `strings.py`.
* **`index()`**: Handles the homepage, including search filtering via FTS5 and recipe listing.
* **`import_page()`**: Renders the user interface for uploading XML files for batch import.
* **`do_import()`**: Manages the temporary storage of uploaded XML files and triggers the import logic.

### `create_recipe.py`
Handles the creation of new recipe entries with robust normalization.
* **`normalize_german_text(text)`**: Standardizes titles by lowercase conversion, replacing umlauts, and collapsing all spaces/special chars into single dashes.
* **`show_form()`**: Processes the `POST` request from `recipe_form.html`, splitting the `category` field by **commas or spaces** to create individual database records.

### `edit_recipe.py`
Manages the modification of existing recipes and media.
* **`handle_image_upload(recipe_id, db)`**: Validates, resizes using Pillow, and saves uploaded recipe images while maintaining aspect ratio.
* **`manage_recipe(id=None)`**: Acts as a unified controller to fetch existing data for the form (GET) or update the database (POST).

### `view_recipe.py`
Handles data retrieval for the detailed display and quick updates.
* **`delete_recipe(id)`**: Removes a recipe; relies on `ON DELETE CASCADE` in the schema to clean up linked ingredients and steps.
* **`update_fast(id)`**: Performs an optimized update of the `annotations` (notes) field directly from the recipe detail page.
* **`show_details(id)`**: Aggregates all recipe data, including formatted ingredient quantities (e.g., `250,0` -> `250`), for the detail view.

### `import_recipe.py`
A migration utility for importing standardized XML cookbook files.
* **`normalize_title(title)`**: Standardizes titles to ensure the "No-Duplicates" feature works by matching the `title_normalized` column.
* **`get_or_create_id(cursor, table, column, value)`**: A helper to ensure master data (units, ingredients, categories) exists before linking them.
* **`parse_amount(amount_str, ingredient_name)`**: Safely converts XML strings to floats, treating empty strings as `0.0`.
* **`import_xml_to_db(xml_file, db_file)`**: Parses the XML structure to populate recipes, steps, and multiple category links.

### `export_recipes_xml.py`
Utility to export the database content back into standardized XML files.
* **`prettify(elem)`**: Uses `minidom` to return a human-readable, indented XML string.
* **`export_database_to_xml(db_file, output_dir)`**: Generates XML files where `amount="0"` is exported as `amount=""`, and the `<categories>` block is only generated if data is present.


## Frontend and HTML Templates

### `base.html`
The master layout containing the global styles, navigation, and shared JavaScript.
* **`addIngredientRow()`**: A JavaScript function that dynamically clones ingredient input rows for the recipe form.
* **`Block: content`**: The primary placeholder where child templates inject their specific HTML.
* **`Global Styles`**: Defines the CSS variable palette (Amber/Charcoal) for the terminal-themed interface.

### `index.html`
The main dashboard and search interface of the application.
* **`Search Form`**: Provides filters for title, category, and ingredients using the FTS5 search engine.
* **`Recipe Grid`**: Displays recipe thumbnails, titles, and "tested" status in a responsive card layout.
* **`Navigation Links`**: Contains prominent buttons for creating new recipes or accessing the import page.

### `recipe_detail.html`
The comprehensive view for a single recipe, including interactive tools.
* **`calculateMengen()`**: A JavaScript calculator that updates ingredient quantities in real-time based on the desired number of servings.
* **`Fast Update Form`**: Allows users to edit the "Notes/Annotations" field directly without leaving the detail page.
* **`Category Tags`**: Renders individual, styled spans for each category linked to the recipe.

### `recipe_form.html`
The unified interface for both creating new recipes and editing existing ones.
* **`filterDatalist()`**: A JavaScript helper that provides "search-as-you-type" suggestions for units, ingredients, and categories.
* **`Dynamic Rows`**: Uses the logic from `base.html` to allow an unlimited number of ingredients and preparation steps.
* **`Datalists`**: Hooks into master data (units, ingredients, categories) to ensure consistent data entry.

### `import.html`
The specialized interface for database migration.
* **`Upload Form`**: A simple, focused form that accepts XML files and routes them to the server-side import logic.
* **`Instructions`**: Displays amber-colored help text (via the translation engine) to guide the user through the upload process.