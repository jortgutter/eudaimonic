import requests
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

API_KEY = "994b40bfa4475cba2cf97ff9dde9a6b2"
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

DB_FILE = "movies1970-2000.db"
MAX_WORKERS = 10  # adjust carefully (5–10 is safe)
REQUEST_TIMEOUT = 15
SIMILAR_LIMIT = 10
RECOMMENDATIONS_LIMIT = 10
CAST_LIMIT = 10
CREW_LIMIT = 10

lock = Lock()

# --- DB SETUP ---
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY,
    title TEXT,
    summary TEXT,
    image_url TEXT,
    vote_average REAL,
    release_date TEXT,
    adult INTEGER
)
""")

def ensure_column(table_name, column_name, column_definition):
    existing_columns = {
        row[1] for row in cur.execute(f"PRAGMA table_info({table_name})")
    }
    if column_name not in existing_columns:
        cur.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_definition}"
        )

ensure_column("movies", "vote_average", "vote_average REAL")
ensure_column("movies", "release_date", "release_date TEXT")
ensure_column("movies", "adult", "adult INTEGER")

cur.execute("""
CREATE TABLE IF NOT EXISTS genres (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS movie_genres (
    movie_id INTEGER,
    genre_id INTEGER,
    PRIMARY KEY (movie_id, genre_id)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    movie_id INTEGER,
    review_text TEXT,
    author TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS movie_keywords (
    movie_id INTEGER,
    keyword_id INTEGER,
    PRIMARY KEY (movie_id, keyword_id)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY,
    name TEXT,
    profile_path TEXT,
    known_for_department TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS movie_people (
    movie_id INTEGER,
    person_id INTEGER,
    credit_type TEXT,
    role_name TEXT,
    credit_order INTEGER,
    PRIMARY KEY (movie_id, person_id, credit_type, role_name)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS similar_movies (
    movie_id INTEGER,
    similar_movie_id INTEGER,
    title TEXT,
    overview TEXT,
    poster_path TEXT,
    PRIMARY KEY (movie_id, similar_movie_id)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS recommended_movies (
    movie_id INTEGER,
    recommended_movie_id INTEGER,
    title TEXT,
    overview TEXT,
    poster_path TEXT,
    PRIMARY KEY (movie_id, recommended_movie_id)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS watch_providers (
    movie_id INTEGER,
    country_code TEXT,
    provider_type TEXT,
    provider_id INTEGER,
    provider_name TEXT,
    logo_path TEXT,
    link TEXT,
    PRIMARY KEY (movie_id, country_code, provider_type, provider_id)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS spoken_languages (
    iso_639_1 TEXT PRIMARY KEY,
    english_name TEXT,
    name TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS movie_spoken_languages (
    movie_id INTEGER,
    language_code TEXT,
    PRIMARY KEY (movie_id, language_code)
)
""")

# NEW: track progress
cur.execute("""
CREATE TABLE IF NOT EXISTS processed_pages (
    year INTEGER,
    page INTEGER,
    PRIMARY KEY (year, page)
)
""")

conn.commit()

# --- API HELPERS ---
def fetch_genres():
    url = f"{BASE_URL}/genre/movie/list?api_key={API_KEY}"
    data = requests.get(url, timeout=REQUEST_TIMEOUT).json()
    for g in data["genres"]:
        cur.execute(
            "INSERT OR IGNORE INTO genres (id, name) VALUES (?, ?)",
            (g["id"], g["name"])
        )
    conn.commit()

def fetch_movies(year, page):
    url = f"{BASE_URL}/discover/movie"
    params = {
        "api_key": API_KEY,
        "primary_release_year": year,
        "page": page
    }
    return requests.get(url, params=params, timeout=REQUEST_TIMEOUT).json()

def fetch_reviews(movie_id):
    url = f"{BASE_URL}/movie/{movie_id}/reviews"
    params = {"api_key": API_KEY}
    return requests.get(url, params=params, timeout=REQUEST_TIMEOUT).json()["results"]

def fetch_keywords(movie_id):
    url = f"{BASE_URL}/movie/{movie_id}/keywords"
    params = {"api_key": API_KEY}
    data = requests.get(url, params=params, timeout=REQUEST_TIMEOUT).json()
    return data.get("keywords", [])

def fetch_credits(movie_id):
    url = f"{BASE_URL}/movie/{movie_id}/credits"
    params = {"api_key": API_KEY}
    return requests.get(url, params=params, timeout=REQUEST_TIMEOUT).json()

def fetch_similar_movies(movie_id):
    url = f"{BASE_URL}/movie/{movie_id}/similar"
    params = {"api_key": API_KEY}
    data = requests.get(url, params=params, timeout=REQUEST_TIMEOUT).json()
    return data.get("results", [])[:SIMILAR_LIMIT]

def fetch_recommendations(movie_id):
    url = f"{BASE_URL}/movie/{movie_id}/recommendations"
    params = {"api_key": API_KEY}
    data = requests.get(url, params=params, timeout=REQUEST_TIMEOUT).json()
    return data.get("results", [])[:RECOMMENDATIONS_LIMIT]

def fetch_watch_providers(movie_id):
    url = f"{BASE_URL}/movie/{movie_id}/watch/providers"
    params = {"api_key": API_KEY}
    data = requests.get(url, params=params, timeout=REQUEST_TIMEOUT).json()
    return data.get("results", {})

def fetch_movie_details(movie_id):
    url = f"{BASE_URL}/movie/{movie_id}"
    params = {"api_key": API_KEY}
    return requests.get(url, params=params, timeout=REQUEST_TIMEOUT).json()

def store_keywords(movie_id, keywords):
    for keyword in keywords:
        cur.execute(
            "INSERT OR IGNORE INTO keywords (id, name) VALUES (?, ?)",
            (keyword["id"], keyword["name"])
        )
        cur.execute(
            "INSERT OR IGNORE INTO movie_keywords (movie_id, keyword_id) VALUES (?, ?)",
            (movie_id, keyword["id"])
        )

def store_people(movie_id, credits):
    cast = credits.get("cast", [])[:CAST_LIMIT]
    crew = credits.get("crew", [])[:CREW_LIMIT]

    for person in cast:
        cur.execute(
            """
            INSERT OR IGNORE INTO people (id, name, profile_path, known_for_department)
            VALUES (?, ?, ?, ?)
        """,
            (
                person["id"],
                person.get("name"),
                person.get("profile_path"),
                person.get("known_for_department")
            )
        )
        cur.execute(
            """
            INSERT OR IGNORE INTO movie_people (movie_id, person_id, credit_type, role_name, credit_order)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                movie_id,
                person["id"],
                "cast",
                person.get("character"),
                person.get("order")
            )
        )

    for person in crew:
        cur.execute(
            """
            INSERT OR IGNORE INTO people (id, name, profile_path, known_for_department)
            VALUES (?, ?, ?, ?)
        """,
            (
                person["id"],
                person.get("name"),
                person.get("profile_path"),
                person.get("known_for_department")
            )
        )
        cur.execute(
            """
            INSERT OR IGNORE INTO movie_people (movie_id, person_id, credit_type, role_name, credit_order)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                movie_id,
                person["id"],
                "crew",
                person.get("job"),
                person.get("order")
            )
        )

def store_related_movies(movie_id, rows, table_name, id_column):
    for related in rows:
        cur.execute(
            f"""
            INSERT OR IGNORE INTO {table_name} (
                movie_id,
                {id_column},
                title,
                overview,
                poster_path
            ) VALUES (?, ?, ?, ?, ?)
        """,
            (
                movie_id,
                related["id"],
                related.get("title"),
                related.get("overview"),
                related.get("poster_path")
            )
        )

def store_watch_providers(movie_id, providers_by_country):
    for country_code, provider_groups in providers_by_country.items():
        for provider_type in ("flatrate", "rent", "buy", "ads", "free"):
            for provider in provider_groups.get(provider_type, []):
                cur.execute(
                    """
                    INSERT OR IGNORE INTO watch_providers (
                        movie_id,
                        country_code,
                        provider_type,
                        provider_id,
                        provider_name,
                        logo_path,
                        link
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        movie_id,
                        country_code,
                        provider_type,
                        provider["provider_id"],
                        provider.get("provider_name"),
                        provider.get("logo_path"),
                        provider_groups.get("link")
                    )
                )

def store_spoken_languages(movie_id, languages):
    for language in languages:
        language_code = language.get("iso_639_1")
        if not language_code:
            continue

        cur.execute(
            """
            INSERT OR IGNORE INTO spoken_languages (iso_639_1, english_name, name)
            VALUES (?, ?, ?)
        """,
            (
                language_code,
                language.get("english_name"),
                language.get("name")
            )
        )
        cur.execute(
            """
            INSERT OR IGNORE INTO movie_spoken_languages (movie_id, language_code)
            VALUES (?, ?)
        """,
            (movie_id, language_code)
        )

# --- WORKER FUNCTION ---
def process_page(year, page):
    try:
        data = fetch_movies(year, page)

        if "results" not in data:
            return

        for m in data["results"]:
            movie_id = m["id"]
            title = m["title"]
            summary = m["overview"]
            image_url = IMAGE_BASE + m["poster_path"] if m["poster_path"] else None
            vote_average = m.get("vote_average")
            release_date = m.get("release_date")
            adult = 1 if m.get("adult", False) else 0

            with lock:
                cur.execute("""
                    INSERT OR REPLACE INTO movies (
                        id,
                        title,
                        summary,
                        image_url,
                        vote_average,
                        release_date,
                        adult
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    movie_id,
                    title,
                    summary,
                    image_url,
                    vote_average,
                    release_date,
                    adult
                ))

                for genre_id in m["genre_ids"]:
                    cur.execute("""
                        INSERT OR IGNORE INTO movie_genres (movie_id, genre_id)
                        VALUES (?, ?)
                    """, (movie_id, genre_id))

            details = {}
            try:
                details["keywords"] = fetch_keywords(movie_id)
            except Exception:
                details["keywords"] = []

            try:
                details["credits"] = fetch_credits(movie_id)
            except Exception:
                details["credits"] = {}

            try:
                details["similar"] = fetch_similar_movies(movie_id)
            except Exception:
                details["similar"] = []

            try:
                details["recommendations"] = fetch_recommendations(movie_id)
            except Exception:
                details["recommendations"] = []

            try:
                details["watch_providers"] = fetch_watch_providers(movie_id)
            except Exception:
                details["watch_providers"] = {}

            try:
                details["movie_details"] = fetch_movie_details(movie_id)
            except Exception:
                details["movie_details"] = {}

            with lock:
                store_keywords(movie_id, details["keywords"])
                store_people(movie_id, details["credits"])
                store_related_movies(movie_id, details["similar"], "similar_movies", "similar_movie_id")
                store_related_movies(
                    movie_id,
                    details["recommendations"],
                    "recommended_movies",
                    "recommended_movie_id"
                )
                store_watch_providers(movie_id, details["watch_providers"])
                store_spoken_languages(
                    movie_id,
                    details["movie_details"].get("spoken_languages", [])
                )

        # OPTIONAL: fetch limited reviews (avoid overload)
        for m in data["results"]:
            if m["vote_count"] > 50:  # filter
                reviews = fetch_reviews(m["id"])[:2]

                with lock:
                    for r in reviews:
                        cur.execute("""
                            INSERT OR IGNORE INTO reviews (id, movie_id, review_text, author)
                            VALUES (?, ?, ?, ?)
                        """, (
                            r["id"],
                            m["id"],
                            r["content"],
                            r["author"]
                        ))

        # mark page as processed
        with lock:
            cur.execute("""
                INSERT OR IGNORE INTO processed_pages (year, page)
                VALUES (?, ?)
            """, (year, page))
            conn.commit()

        print(f"✔ Done {year} page {page}")

        time.sleep(0.2)  # rate safety

    except Exception as e:
        print(f"Error {year}-{page}: {e}")

# --- MAIN ---
def main():
    fetch_genres()

    jobs = []

    # define your range
    for year in range(1970, 2000):
        for page in range(1, 100):  # 20 pages per year
            # skip already processed
            cur.execute("""
                SELECT 1 FROM processed_pages
                WHERE year=? AND page=?
            """, (year, page))

            if cur.fetchone() is None:
                jobs.append((year, page))

    print(f"{len(jobs)} pages to process...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(process_page, year, page)
            for year, page in jobs
        ]

        for f in as_completed(futures):
            pass

    print("Done!")

if __name__ == "__main__":
    main()