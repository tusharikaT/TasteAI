import os
import sys
import csv
import json
import sqlite3
import requests

# Increase CSV field size limit for large review/menu text fields
csv.field_size_limit(10 * 1024 * 1024)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
CSV_FILE_PATH = os.path.join(DATA_DIR, "zomato.csv")
DB_FILE_PATH = os.path.join(DATA_DIR, "zomato.db")
DATASET_URL = "https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation/resolve/main/zomato.csv"

def ensure_directories():
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"Directory verified: {DATA_DIR}")

def download_dataset():
    if os.path.exists(CSV_FILE_PATH):
        print(f"Found existing cached CSV at: {CSV_FILE_PATH}. Skipping download.")
        return

    print("Downloading Zomato dataset from Hugging Face...")
    print(f"Source URL: {DATASET_URL}")
    print("This may take a moment depending on connection speed...")

    try:
        response = requests.get(DATASET_URL, stream=True)
        response.raise_for_status()

        total_bytes = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(CSV_FILE_PATH, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_bytes > 0:
                        percent = (downloaded / total_bytes) * 100
                        print(f"Downloaded: {downloaded / (1024 * 1024):.1f} MB / {total_bytes / (1024 * 1024):.1f} MB ({percent:.1f}%)", end="\r")
                    else:
                        print(f"Downloaded: {downloaded / (1024 * 1024):.1f} MB", end="\r")
        print("\nDownload completed successfully.")
    except Exception as e:
        if os.path.exists(CSV_FILE_PATH):
            os.remove(CSV_FILE_PATH)
        print(f"\nError downloading dataset: {e}")
        raise

def parse_rating(rate_str):
    if not rate_str or rate_str.strip() in ("NEW", "-", ""):
        return None
    try:
        # Extract the score before the slash (e.g. "4.1/5" -> 4.1)
        if "/" in rate_str:
            rate_str = rate_str.split("/")[0]
        return float(rate_str.strip())
    except ValueError:
        return None

def parse_cost(cost_str):
    if not cost_str or cost_str.strip() == "":
        return None
    try:
        # Remove commas and non-numeric details (e.g., "1,200" -> 1200)
        cost_cleaned = "".join(c for c in cost_str if c.isdigit())
        return int(cost_cleaned) if cost_cleaned else None
    except ValueError:
        return None

def parse_cuisines(cuisines_str):
    if not cuisines_str or cuisines_str.strip() == "":
        return []
    # Split by comma and strip extra whitespaces
    return [c.strip() for c in cuisines_str.split(",") if c.strip()]

def seed_database():
    print("Initializing SQLite Database...")
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT,
            online_order INTEGER,
            book_table INTEGER,
            rating REAL,
            votes INTEGER,
            location TEXT,
            cuisines TEXT,  -- JSON formatted string array
            average_cost INTEGER,
            city TEXT
        );
    """)

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_restaurants_city ON restaurants(city);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_restaurants_rating ON restaurants(rating);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_restaurants_cost ON restaurants(average_cost);")
    conn.commit()

    print("Seeding database from CSV file...")
    
    # Read the CSV in utf-8 encoding
    # Some rows might contain encoding issues, use 'utf-8-sig' or handle errors
    batch = []
    batch_size = 5000
    total_records = 0

    with open(CSV_FILE_PATH, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                name = row.get("name", "").strip()
                if not name:
                    continue  # Skip rows without name
                
                address = row.get("address", "").strip()
                online_order = 1 if row.get("online_order", "").strip().lower() == "yes" else 0
                book_table = 1 if row.get("book_table", "").strip().lower() == "yes" else 0
                rating = parse_rating(row.get("rate"))
                votes = int(row.get("votes", "0").strip() or 0)
                location = row.get("location", "").strip()
                
                cuisines = parse_cuisines(row.get("cuisines"))
                cuisines_json = json.dumps(cuisines)
                
                average_cost = parse_cost(row.get("approx_cost(for two people)"))
                city = row.get("listed_in(city)", "").strip()

                batch.append((
                    name, address, online_order, book_table, 
                    rating, votes, location, cuisines_json, 
                    average_cost, city
                ))

                if len(batch) >= batch_size:
                    cursor.executemany("""
                        INSERT INTO restaurants (
                            name, address, online_order, book_table, 
                            rating, votes, location, cuisines, 
                            average_cost, city
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, batch)
                    conn.commit()
                    total_records += len(batch)
                    print(f"Inserted {total_records} records into database...")
                    batch = []

            except Exception as e:
                # Log any corrupt lines and continue
                print(f"Skipping row due to error: {e}")

        # Insert final chunk
        if batch:
            cursor.executemany("""
                INSERT INTO restaurants (
                    name, address, online_order, book_table, 
                    rating, votes, location, cuisines, 
                    average_cost, city
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            conn.commit()
            total_records += len(batch)

    print(f"Seeding finished. Total records loaded: {total_records}")
    conn.close()

if __name__ == "__main__":
    ensure_directories()
    try:
        download_dataset()
        seed_database()
        print("Ingestion pipeline executed successfully!")
    except Exception as e:
        print(f"Ingestion failed: {e}")
