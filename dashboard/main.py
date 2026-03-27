# coding: utf-8
from flask import Flask, request
from strings import TRANSLATIONS

app = Flask(__name__)

def get_lang():
    accept = request.headers.get('Accept-Language', '')
    return 'de' if 'de' in accept.lower() else 'en'

@app.route('/')
def index():
    lang = get_lang()
    t = TRANSLATIONS.get(lang, TRANSLATIONS['en'])
    
    return f"""
    <!DOCTYPE html>
    <html lang="{lang}">
    <head>
        <meta charset="UTF-8">
        <title>Geheimlabor Control</title>
        <style>
            body {{ background: #000; color: #ffb000; font-family: monospace; text-align: center; padding: 50px; margin: 0; }}
            h1 {{ border-bottom: 2px solid #ffb000; display: inline-block; padding-bottom: 10px; text-transform: uppercase; }}
            .nav {{ margin-top: 30px; display: flex; justify-content: center; gap: 20px; }}
            .tag {{ border: 2px solid #ffb000; padding: 15px 25px; text-decoration: none; color: #ffb000; font-weight: bold; transition: all 0.3s; text-transform: uppercase; }}
            .tag:hover {{ background: #ffb000; color: #000; }}
            .status {{ margin-top: 50px; font-size: 0.8em; opacity: 0.6; }}
        </style>
    </head>
    <body>
        <h1>{t['welcome']}</h1>
        <div class="nav">
            <a href="/kochbuch/" class="tag">{t['btn_kochbuch']}</a>
            <a href="#" class="tag" style="opacity: 0.3; cursor: not-allowed;">{t['btn_inventar']}</a>
        </div>
        <div class="status">SYSTEM READY // SECTOR 7G // 2026-03-16</div>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

