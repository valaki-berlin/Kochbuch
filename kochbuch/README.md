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
The core Flask server that handles application configuration, blueprint registration, and top-level routing.

* **`inject_globals()` / `inject_translations()`**: Makes the translation function `t()` globally available in all HTML templates.
* **`close_connection(exception)`**: Ensures the SQLite database connection is closed after every request.
* **`get_string(key)`**: Retrieves the translated string based on the user's browser language settings.
* **`index()`**: Handles the main landing page and processes basic searches for titles, categories, or ingredients.
* **`import_page()`**: Renders the upload form for importing recipes via XML files.
* **`do_import()`**: Manages the XML file upload process, temporary storage, and triggers the import logic.
* **`extended_search()`**: Provides a specialized search interface specifically for filtering recipes by category grids.

### `utils.py`
A collection of shared utility functions for data processing, image handling, and database orchestration.

* **`handle_image_upload(...)`**: Processes uploaded images, resizes them to a standard width, and updates the database records.
* **`normalize_title(title)`**: Standardizes recipe titles for URLs and duplicate checks by removing special characters and handling German umlauts.
* **`prettify_xml(elem)`**: Formats an XML ElementTree into a human-readable, indented string.
* **`get_categories_string(db, recipe_id)`**: Fetches all categories for a specific recipe and returns them as a single comma-separated string.
* **`get_complete_recipe(db, recipe_id)`**: Fetches all consolidated data (base info, ingredients, steps, categories) for a recipe into a single dictionary.
* **`save_recipe_categories(...)`**: Synchronizes the relationship between a recipe and its categories based on user input.
* ****`save_complete_recipe(...)`**: Acts as the main coordinator to save all parts of a recipe from a form submission.
* **`update_recipe_base_data(...)`**: Updates core recipe fields like title, servings, and notes in the database.
* **`save_recipe_ingredients(...)`**: Manages the list of ingredients, including quantities, units, and master data entry.
* **`save_recipe_steps(...)`**: Parses a text block into individual numbered cooking steps and saves them to the database.

### `view_recipe.py`
Handles logic for displaying recipe details and performing quick actions like deletions or minor updates.

* **`delete_recipe(id)`**: Removes a recipe from the database, relying on SQL cascades to clean up linked ingredients and steps.
* **`update_fast(id)`**: Allows users to update the recipe's notes directly from the detail view without entering the full edit mode.
* **`show_details(id)`**: Prepares recipe data for display, including formatting ingredients and identifying sub-headings (headers).

### `edit_recipe.py`
Manages the logic for the unified recipe creation and editing form.

* **`manage_recipe(id=None)`**: Handles GET requests to display the form and POST requests to save new or modified recipe data.

### Data Exchange: `import_recipe.py` & `export_xml.py`
Modules dedicated to importing from and exporting to structured XML formats.

* **`get_or_create_id(...)`**: Finds a record ID for units/ingredients or creates a new one if it doesn't exist.
* **`parse_amount(...)`**: Converts string-based quantities into floats for database compatibility.
* **`import_xml_to_db(...)`**: Parses an XML file and inserts all contained recipe data into the SQLite database.
* **`prettify(elem)`** (in export): A helper function to ensure exported XML files are properly indented.
* **`export_database_to_xml(...)`**: Iterates through the entire database and generates individual XML files for every recipe.

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

### `show.html`
The comprehensive view for a single recipe, including interactive tools.
* **`calculateAmount()`**: A JavaScript calculator that updates ingredient quantities in real-time based on the desired number of servings.
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
