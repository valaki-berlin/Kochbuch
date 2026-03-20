# coding: utf-8
import sqlite3
from flask import Flask, render_template

app = Flask(__name__)

def get_db_connection():
    # Connect to the local SQLite file
    conn = sqlite3.connect('Rezepte.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db_connection()
    # Create table if it doesn't exist yet
    conn.execute('''CREATE TABLE IF NOT EXISTS rezepte 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     titel TEXT NOT NULL, 
                     zutaten TEXT)''')
    
    # Get all recipes (currently empty)
    rezepte = conn.execute('SELECT * FROM rezepte').fetchall()
    conn.close()
    
    # Return a simple list for now
    html = "<h1>Mein Kochbuch</h1>"
    if not rezepte:
        html += "<p>Noch keine Rezepte da. Füge bald welche hinzu!</p>"
    return html

if __name__ == '__main__':
    app.run(host='0.0.0.0')

