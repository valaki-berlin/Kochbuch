# Kochbuch Project 2026

This repository contains the software suite for the "Kochbuch" (recipe book) priject Raspberry Pi. The system is modular and runs on a Raspberry Pi 2 using a macOS-style English UI environment.

## Project Structure

### 1. Dashboard (`/dashboard`)
The central entry portal for the system.
- **Tech Stack:** Python Flask / Gunicorn.
- **Design:** Minimalist "Amber Terminal" aesthetic.
- **Features:** Automatic localization (DE/EN) based on browser headers, quick-access navigation for sub-modules.

### 2. Cookbook (`/kochbuch`)
The recipe management module for the Spieltisch.
- **Tech Stack:** Python Flask, SQLite database.
- **Features:** Management of recipes, ingredients, and categories.

### 3. Services (`/services`)
Contains configuration files for system integration.
- **Target Directory:** `/etc/systemd/system/`
- **Files:** `dashboard.service`, `kochbuch.service`.
- These services ensure that the web applications load automatically on boot and restart in case of failure.

## Installation & Setup

1. **Clone the Repository:**
   ```bash
   git clone [https://github.com/valaki-berlin/Kochbuch.git](https://github.com/valaki-berlin/Kochbuch.git) ~/new_repo
