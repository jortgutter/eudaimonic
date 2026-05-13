
import * as SQLite from 'expo-sqlite';

const db = SQLite.openDatabaseSync('movies1970-2000.db');

export function initDb() {
  db.execSync(`PRAGMA journal_mode = WAL;`);
  db.execSync(`PRAGMA synchronous = NORMAL;`);
}

export type TraitOptions = {
  Wisdom?: boolean;
  Courage?: boolean;
  Humanity?: boolean;
  Justice?: boolean;
  Temperance?: boolean;
  Transcendence?: boolean;
};

export type ScoredMovie = {
  id: number;
  title: string;
  summary: string;
  image_url: string;
  vote_average: number;
  release_date: string;
  adult: number;
  match_score: number;
  Humanity: number;
  Wisdom: number;
  Courage: number;
  Temperance: number;
  Transcendence: number;
  Justice :number;
};

export function getTopMoviesByTraits(
  traits: TraitOptions
): ScoredMovie[] {

  const enabledColumns: string[] = [];

  if (traits.Wisdom) {
    enabledColumns.push(`COALESCE(ms."Wisdom", 0)`);
  }

  if (traits.Courage) {
    enabledColumns.push(`COALESCE(ms."Courage", 0)`);
  }

  if (traits.Humanity) {
    enabledColumns.push(`COALESCE(ms."Humanity", 0)`);
  }

  if (traits.Justice) {
    enabledColumns.push(`COALESCE(ms."Justice", 0)`);
  }

  if (traits.Temperance) {
    enabledColumns.push(`COALESCE(ms."Temperance", 0)`);
  }

  if (traits.Transcendence) {
    enabledColumns.push(`COALESCE(ms."Transcendence", 0)`);
  }

  // No traits enabled
  if (enabledColumns.length === 0) {
    return [];
  }

  const sumExpr = enabledColumns.join(" + ");
  const scoreExpression = `(${sumExpr}) / ${enabledColumns.length}`;

  const query = `
    SELECT
      m.*,
      ${scoreExpression} AS match_score
    FROM movies m
    JOIN movie_virtue_scores_wide ms
      ON ms.movie_id = m.id
    ORDER BY match_score DESC
    LIMIT 20
  `;

  return db.getAllSync(query) as ScoredMovie[];
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