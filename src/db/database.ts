
import * as SQLite from 'expo-sqlite';
import moviesData from '../data/movies.json';
const db = SQLite.openDatabaseSync('movies.db');

export function initDb() {
  db.execSync(`
    CREATE TABLE IF NOT EXISTS movies (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT,
      year INTEGER,
      rating REAL,
      genre TEXT,
      humanity REAL,
      courage REAL,
      justice REAL,
      purpose REAL,
      restraint REAL,
      wisdom REAL
    );
  `);
  seedIfEmpty();
}

function seedIfEmpty() {

  const result = db.getFirstSync(
    'SELECT COUNT(*) as count FROM movies'
  );

if (!result || result.count === 0) {
    seedFromJson();
  }
}

function seedFromJson() {
  for (const movie of moviesData) {
    db.runSync(
      `INSERT INTO movies 
      (title, year, rating, genre, humanity, courage, justice, purpose, restraint, wisdom)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        movie.title,
        movie.year,
        movie.rating,
        movie.genre,
        movie.humanity,
        movie.courage,
        movie.justice,
        movie.purpose,
        movie.restraint,
        movie.wisdom
      ]
    );
  }
}


export function getMovies() {
  return db.getAllSync('SELECT * FROM movies');
}

export function getMovieById(id: number) {
  return db.getFirstSync(
    'SELECT * FROM movies WHERE id = ?',
    [id]
  );


}