# database.py
import sqlite3
from flask import g

DATABASE = 'db/RezeptDB.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row  # Erlaubt Zugriff via Spaltennamen
        db.execute("PRAGMA foreign_keys = ON;")
    return db
