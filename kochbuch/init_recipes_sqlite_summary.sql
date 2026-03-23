
-- ===========================================
-- Recipe DB (SQLite) - Initialization Script (Flat Categories + Optional Relations)
-- ===========================================
-- Notes:
-- * Enable foreign keys per connection: PRAGMA foreign_keys = ON;
-- * Titles are globally unique (case-insensitive via COLLATE NOCASE).
-- * Categories are flat (no parent_id). Optional category_relation allows building arbitrary hierarchies
--   (e.g., 'Chinesisch' -> 'Rindfleisch' and 'Rindfleisch' -> 'Chinesisch').
-- * Comments are in English as requested.

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

BEGIN;

-- ===========================================
-- Meta: Schema Versioning
-- ===========================================
CREATE TABLE IF NOT EXISTS schema_info (
    version      INTEGER PRIMARY KEY,
    installed_at TEXT DEFAULT CURRENT_TIMESTAMP
);
INSERT OR IGNORE INTO schema_info (version) VALUES (1);

-- ===========================================
-- Core: Recipes
-- ===========================================
CREATE TABLE IF NOT EXISTS recipe (
    recipe_id     INTEGER PRIMARY KEY,                 -- rowid
    title         TEXT NOT NULL COLLATE NOCASE,        -- case-insensitive compares
    -- title_normalized: used for German search (e.g., 'spätzle' -> 'spaetzle')
    title_normalized   TEXT NOT NULL COLLATE NOCASE,
    description   TEXT,
    annotations   TEXT,
    servings      INTEGER CHECK (servings > 0),
    prep_minutes  INTEGER CHECK (prep_minutes >= 0),
    cook_minutes  INTEGER CHECK (cook_minutes >= 0),
    is_tested     INTEGER NOT NULL DEFAULT 1 CHECK (is_tested IN (0,1)),
    created_at         TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Titles must be unique globally (case-insensitive)
CREATE UNIQUE INDEX IF NOT EXISTS ux_recipe_title ON recipe(title);
CREATE INDEX IF NOT EXISTS ix_recipe_title_norm ON recipe(title_normalized);

-- Keep updated_at fresh on UPDATE (uses a follow-up UPDATE; recursive triggers are OFF by default)
CREATE TRIGGER IF NOT EXISTS trg_recipe_touch_updated_at
AFTER UPDATE ON recipe
FOR EACH ROW
BEGIN
    UPDATE recipe
    SET updated_at = CURRENT_TIMESTAMP
    WHERE recipe_id = NEW.recipe_id;
END;

-- ===========================================
-- Steps: ordered instructions per recipe
-- ===========================================
CREATE TABLE IF NOT EXISTS recipe_step (
    step_id       INTEGER PRIMARY KEY,
    recipe_id     INTEGER NOT NULL,
    step_no       INTEGER NOT NULL CHECK (step_no >= 1),
    instruction   TEXT NOT NULL,
    timer_minutes INTEGER CHECK (timer_minutes >= 0),
    FOREIGN KEY (recipe_id) REFERENCES recipe(recipe_id) ON DELETE CASCADE,
    UNIQUE (recipe_id, step_no)
);
CREATE INDEX IF NOT EXISTS ix_recipe_step_recipe ON recipe_step(recipe_id);

-- ===========================================
-- Ingredients master
-- ===========================================
CREATE TABLE IF NOT EXISTS ingredient (
    ingredient_id INTEGER PRIMARY KEY,
    name          TEXT NOT NULL COLLATE NOCASE UNIQUE,
    is_active     INTEGER NOT NULL DEFAULT 1
);

-- ===========================================
-- Units & conversion (simple)
-- ===========================================
CREATE TABLE IF NOT EXISTS unit (
    unit_id        INTEGER PRIMARY KEY,
    name           TEXT NOT NULL COLLATE NOCASE UNIQUE,  -- e.g., 'gramm', 'milliliter', 'piece'
    symbol         TEXT,                                  -- e.g., 'g', 'ml'
    group_code     TEXT NOT NULL,                         -- 'mass'|'volume'|'count'
    is_base        INTEGER NOT NULL DEFAULT 0,
    factor_to_base REAL NOT NULL DEFAULT 1.0 CHECK (factor_to_base > 0)
);

-- ===========================================
-- Recipe <-> Ingredient with quantities & units
-- ===========================================
CREATE TABLE IF NOT EXISTS recipe_ingredient (
    recipe_id        INTEGER NOT NULL,
    ingredient_id    INTEGER NOT NULL,
    position         INTEGER NOT NULL DEFAULT 1,         -- allows repeated ingredient lines
    quantity         REAL NOT NULL CHECK (quantity > 0),
    unit_id          INTEGER NOT NULL,
    preparation_note TEXT,
    PRIMARY KEY (recipe_id, ingredient_id, position),
    FOREIGN KEY (recipe_id)     REFERENCES recipe(recipe_id)         ON DELETE CASCADE,
    FOREIGN KEY (ingredient_id) REFERENCES ingredient(ingredient_id) ON DELETE RESTRICT,
    FOREIGN KEY (unit_id)       REFERENCES unit(unit_id)             ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS ix_recipe_ingredient_recipe
    ON recipe_ingredient(recipe_id);
CREATE INDEX IF NOT EXISTS ix_recipe_ingredient_ingredient
    ON recipe_ingredient(ingredient_id);

-- ===========================================
-- Categories (flat) + optional relations for flexible hierarchies
-- ===========================================
CREATE TABLE IF NOT EXISTS category (
    category_id INTEGER PRIMARY KEY,
    name        TEXT NOT NULL COLLATE NOCASE UNIQUE
);

CREATE TABLE IF NOT EXISTS recipe_category (
    recipe_id   INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    PRIMARY KEY (recipe_id, category_id),
    FOREIGN KEY (recipe_id)   REFERENCES recipe(recipe_id)   ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES category(category_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_recipe_category_category
    ON recipe_category(category_id);

-- Optional: category relations to build arbitrary navigations/trees
CREATE TABLE IF NOT EXISTS category_relation (
    from_category_id INTEGER NOT NULL,
    to_category_id   INTEGER NOT NULL,
    relation_type    TEXT NOT NULL DEFAULT 'related', -- 'related'|'broader'|'narrower'|'see_also'
    PRIMARY KEY (from_category_id, to_category_id, relation_type),
    FOREIGN KEY (from_category_id) REFERENCES category(category_id) ON DELETE CASCADE,
    FOREIGN KEY (to_category_id)   REFERENCES category(category_id) ON DELETE CASCADE,
    CHECK (relation_type IN ('related','broader','narrower','see_also'))
);
CREATE INDEX IF NOT EXISTS ix_cat_rel_from ON category_relation(from_category_id);
CREATE INDEX IF NOT EXISTS ix_cat_rel_to   ON category_relation(to_category_id);

-- ===========================================
-- Optional: Tags (free-form keywords)
-- ===========================================
CREATE TABLE IF NOT EXISTS tag (
    tag_id INTEGER PRIMARY KEY,
    name   TEXT NOT NULL COLLATE NOCASE UNIQUE
);

CREATE TABLE IF NOT EXISTS recipe_tag (
    recipe_id INTEGER NOT NULL,
    tag_id    INTEGER NOT NULL,
    PRIMARY KEY (recipe_id, tag_id),
    FOREIGN KEY (recipe_id) REFERENCES recipe(recipe_id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id)    REFERENCES tag(tag_id)       ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_recipe_tag_tag ON recipe_tag(tag_id);

-- ===========================================
-- Optional: Images (one primary per recipe)
-- ===========================================
CREATE TABLE IF NOT EXISTS recipe_image (
    image_id   INTEGER PRIMARY KEY,
    recipe_id  INTEGER NOT NULL,
    url        TEXT NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 0,   -- 0/1 boolean
    alt_text   TEXT,
    width      INTEGER,
    height     INTEGER,
    FOREIGN KEY (recipe_id) REFERENCES recipe(recipe_id) ON DELETE CASCADE
);

-- one primary image per recipe (partial unique index)
CREATE UNIQUE INDEX IF NOT EXISTS ux_recipe_image_primary
    ON recipe_image(recipe_id)
    WHERE is_primary = 1;

-- ===========================================
-- Helpful search indexes (non-FTS)
-- ===========================================
CREATE INDEX IF NOT EXISTS ix_recipe_desc_lower
    ON recipe(LOWER(COALESCE(description, '')));
CREATE INDEX IF NOT EXISTS ix_tag_name_lower
    ON tag(LOWER(name));
CREATE INDEX IF NOT EXISTS ix_category_name_lower
    ON category(LOWER(name));

-- ===========================================
-- Seed Data (minimal, incl. flexible categories)
-- ===========================================
-- Units
INSERT OR IGNORE INTO unit(name, symbol, group_code, is_base, factor_to_base) VALUES
 ('Gramm','g','mass',1,1.0),
 ('Kilogramm','kg','mass',0,1000.0),
 ('Milliliter','ml','volume',1,1.0),
 ('Liter','l','volume',0,1000.0),
 ('Teelöffel','tsp','volume',0,5.0),
 ('Esslöffel','tbsp','volume',0,15.0),
 ('Stück','pc','count',1,1.0);

-- Ingredients
INSERT OR IGNORE INTO ingredient(name) VALUES
 ('Tomate'),('Olivenöl'),('Knoblauch'),('Spaghetti'),('Basilikum'),('Salz'),('Pfeffer'),
 ('Rindfleisch'),('Zwiebel');

-- Categories (flat)
INSERT OR IGNORE INTO category(name) VALUES
 ('Italienisch'),('Pasta'),('Dessert'),('Chinesisch'),('Rindfleisch');

-- Optional relations (demonstrate interchangeable hierarchies)
-- Italienisch <-> Pasta (broader/narrower pair)
INSERT OR IGNORE INTO category_relation(from_category_id, to_category_id, relation_type)
SELECT c1.category_id, c2.category_id, 'broader'
FROM category c1, category c2
WHERE c1.name='Italienisch' AND c2.name='Pasta';

-- INSERT OR IGNORE INTO category_relation(from_category_id, to_category_id, relation_type)
-- SELECT c2.category_id, c1.category_id, 'narrower'
-- FROM category c1, category c2
-- WHERE c1.name='Italienisch' AND c2.name='Pasta';

-- Chinesisch <-> Rindfleisch (both directions as 'related')
-- INSERT OR IGNORE INTO category_relation(from_category_id, to_category_id, relation_type)
-- SELECT c1.category_id, c2.category_id, 'related'
-- FROM category c1, category c2
-- WHERE c1.name='Chinesisch' AND c2.name='Rindfleisch';

-- INSERT OR IGNORE INTO category_relation(from_category_id, to_category_id, relation_type)
-- SELECT c2.category_id, c1.category_id, 'related'
-- FROM category c1, category c2
-- WHERE c1.name='Chinesisch' AND c2.name='Rindfleisch';

-- Tags
-- INSERT OR IGNORE INTO tag(name) VALUES ('schnell'), ('weeknight'), ('vegetarian');

-- Example recipe 1: Spaghetti Aglio e Olio (Italienisch, Pasta)
INSERT INTO recipe(title, title_normalized, description, servings, prep_minutes, cook_minutes)
VALUES ('Spaghetti Aglio e Olio','Spaghetti Aglio e Olio','Spaghetti mit Knoblauch und Olivenöl',2,5,10);

INSERT INTO recipe_step(recipe_id, step_no, instruction) VALUES
 ((SELECT recipe_id FROM recipe WHERE title='Spaghetti Aglio e Olio'),1,'Boil spaghetti in Salzed water.'),
 ((SELECT recipe_id FROM recipe WHERE title='Spaghetti Aglio e Olio'),2,'Sauté Knoblauch in Olivenöl.'),
 ((SELECT recipe_id FROM recipe WHERE title='Spaghetti Aglio e Olio'),3,'Combine pasta with oil and Knoblauch, season, serve.');

INSERT INTO recipe_ingredient(recipe_id, ingredient_id, position, quantity, unit_id, preparation_note)
SELECT r.recipe_id, i.ingredient_id, 1, 200,
       (SELECT unit_id FROM unit WHERE name='Gramm'), NULL
FROM recipe r, ingredient i
WHERE r.title='Spaghetti Aglio e Olio' AND i.name='Spaghetti';

INSERT INTO recipe_ingredient(recipe_id, ingredient_id, position, quantity, unit_id, preparation_note)
SELECT r.recipe_id, i.ingredient_id, 2, 3,
       (SELECT unit_id FROM unit WHERE name='Esslöffel'), NULL
FROM recipe r, ingredient i
WHERE r.title='Spaghetti Aglio e Olio' AND i.name='Olivenöl';

INSERT INTO recipe_ingredient(recipe_id, ingredient_id, position, quantity, unit_id, preparation_note)
SELECT r.recipe_id, i.ingredient_id, 4, 1,
       (SELECT unit_id FROM unit WHERE name='Teelöffel'), NULL
FROM recipe r, ingredient i
WHERE r.title='Spaghetti Aglio e Olio' AND i.name='Salz';

INSERT INTO recipe_ingredient(recipe_id, ingredient_id, position, quantity, unit_id, preparation_note)
SELECT r.recipe_id, i.ingredient_id, 5, 0.5,
       (SELECT unit_id FROM unit WHERE name='Teelöffel'), 'gemahlen'
FROM recipe r, ingredient i
WHERE r.title='Spaghetti Aglio e Olio' AND i.name='Pfeffer';

INSERT OR IGNORE INTO recipe_category(recipe_id, category_id)
SELECT r.recipe_id, c.category_id
FROM recipe r, category c
WHERE r.title='Spaghetti Aglio e Olio' AND c.name IN ('Pasta','Italienisch');

-- INSERT OR IGNORE INTO recipe_tag(recipe_id, tag_id)
-- SELECT r.recipe_id, t.tag_id
-- FROM recipe r, tag t
-- WHERE r.title='Spaghetti Aglio e Olio' AND t.name IN ('quick','weeknight','vegetarian');

INSERT INTO recipe_image(recipe_id, url, is_primary, alt_text)
SELECT r.recipe_id, 'https://example.com/images/aglio-olio.jpg', 1, 'Spaghetti Aglio e Olio'
FROM recipe r WHERE r.title='Spaghetti Aglio e Olio';

-- Example recipe 2: Rindfleisch Stir-Fry (Chinesisch, Rindfleisch)

-- COMMIT;

-- ===========================================
-- Optional: Full-Text Search (FTS5) for title/description
-- Remove the leading dashes to enable

CREATE VIRTUAL TABLE recipe_fts 
USING fts5(title, description, content='recipe', content_rowid='recipe_id');

-- Initial load 
INSERT INTO recipe_fts(rowid, title, description) 
SELECT recipe_id, title, COALESCE(description,'') FROM recipe;

-- Triggers to keep FTS in sync with recipe table 
CREATE TRIGGER IF NOT EXISTS trg_recipe_ai_fts 
AFTER INSERT ON recipe BEGIN 
  INSERT INTO recipe_fts(rowid, title, description) 
  VALUES (NEW.recipe_id, NEW.title, COALESCE(NEW.description,'')); 
END;

CREATE TRIGGER IF NOT EXISTS trg_recipe_ad_fts 
AFTER DELETE ON recipe BEGIN 
  INSERT INTO recipe_fts(recipe_fts, rowid, title, description) 
  VALUES ('delete', OLD.recipe_id, OLD.title, COALESCE(OLD.description,'')); 
END;

CREATE TRIGGER IF NOT EXISTS trg_recipe_au_fts 
AFTER UPDATE ON recipe BEGIN 
  INSERT INTO recipe_fts(recipe_fts, rowid, title, description) 
  VALUES ('delete', OLD.recipe_id, OLD.title, COALESCE(OLD.description,'')); 
  INSERT INTO recipe_fts(rowid, title, description) 
  VALUES (NEW.recipe_id, NEW.title, COALESCE(NEW.description,'')); 
END;

-- Sync Triggers for FTS5
CREATE TRIGGER IF NOT EXISTS trg_recipe_ai_fts AFTER INSERT ON recipe BEGIN
  INSERT INTO recipe_fts(rowid, title, description) VALUES (NEW.recipe_id, NEW.title, NEW.description);
END;
CREATE TRIGGER IF NOT EXISTS trg_recipe_ad_fts AFTER DELETE ON recipe BEGIN
  INSERT INTO recipe_fts(recipe_fts, rowid, title, description) VALUES ('delete', OLD.recipe_id, OLD.title, OLD.description);
END;
CREATE TRIGGER IF NOT EXISTS trg_recipe_au_fts AFTER UPDATE ON recipe BEGIN
  INSERT INTO recipe_fts(recipe_fts, rowid, title, description) VALUES ('delete', OLD.recipe_id, OLD.title, OLD.description);
  INSERT INTO recipe_fts(rowid, title, description) VALUES (NEW.recipe_id, NEW.title, NEW.description);
END;

INSERT OR IGNORE INTO ingredient(name) VALUES ('Kürbis'), ('Olivenöl'), ('Salz');

-- Note how we provide the normalized title 'kuerbis-suppe' for easier searching
INSERT INTO recipe(title, title_normalized, description, servings, prep_minutes, cook_minutes)
	VALUES ('Kürbis-Suppe', 'kuerbis-suppe', 'Wärmende Suppe für den Herbst', 4, 15, 30);

COMMIT;

