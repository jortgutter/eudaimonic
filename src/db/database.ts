

const DEFAULT_HOST = 'http://localhost:8000';

const API_BASE_URL = DEFAULT_HOST;

const API_V1_BASE = `${API_BASE_URL}/api/v1`;

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
  vote_average: number | null;
  release_date: string;
  adult: number;
  match_score: number;
  Humanity: number;
  Wisdom: number;
  Courage: number;
  Temperance: number;
  Transcendence: number;
  Justice: number;
};

export type CatalogMovie = {
  id: number;
  title: string;
  summary?: string | null;
  image_url?: string | null;
  vote_average?: number | null;
  release_date?: string | null;
  adult?: boolean;
  genres?: string[];
};

export type TmdbMovieSummary = {
  id: number;
  title: string;
  overview?: string | null;
  poster_url?: string | null;
  release_date?: string | null;
  vote_average: number;
  popularity: number;
  genre_ids: number[];
};

type ImportedMovieResponse = {
  movie: CatalogMovie;
  virtue_scores?: VirtueScoresResponse['virtue_scores'];
};

type VirtueScoresResponse = {
  virtue_scores?: {
    wisdom?: number | null;
    courage?: number | null;
    humanity?: number | null;
    justice?: number | null;
    temperance?: number | null;
    transcendence?: number | null;
  };
};

export type VirtueScores = {
  wisdom: number;
  courage: number;
  humanity: number;
  justice: number;
  temperance: number;
  transcendence: number;
};

async function fetchJson<T>(url: string, init?: RequestInit, timeoutMs = 15000): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  const requestInit: RequestInit = {
    ...init,
    signal: init?.signal ?? controller.signal,
  };

  let response: Response;
  try {
    response = await fetch(url, requestInit);
  } catch (err) {
    if (controller.signal.aborted) {
      const msg = `Request timed out after ${timeoutMs}ms when fetching ${url}`;
      console.error(msg);
      throw new Error(msg);
    }

    const msg = `Network error when fetching ${url}: ${err}`;
     
    console.error(msg);
    throw new Error(msg);
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    const text = await response.text().catch(() => '<no body>');
    const msg = `Request failed (${response.status}) for ${url}: ${text}`;
     
    console.error(msg);
    throw new Error(msg);
  }

  return (await response.json()) as T;
}

export async function getCatalogMovies(limit = 100): Promise<CatalogMovie[]> {
  return fetchJson<CatalogMovie[]>(`${API_V1_BASE}/movies?skip=0&limit=${limit}`);
}

export async function searchMovies(
  query: string,
  skip = 0,
  limit = 50
): Promise<CatalogMovie[]> {
  const params = new URLSearchParams({
    q: query,
    skip: String(skip),
    limit: String(limit),
  });

  return fetchJson<CatalogMovie[]>(
    `${API_V1_BASE}/movies/search?${params.toString()}`
  );
}

export async function searchCatalogMovies(
  query: string,
  skip = 0,
  limit = 50
): Promise<CatalogMovie[]> {
  const q = query.trim();

  if (!q) {
    // empty query: let caller decide fallback behavior
    return [];
  }

  const params = new URLSearchParams({
    q,
    skip: String(skip),
    limit: String(limit),
  });

  return fetchJson<CatalogMovie[]>(
    `${API_V1_BASE}/movies/search?${params.toString()}`
  );
}

export async function searchTmdbMovies(
  query: string,
  page = 1,
): Promise<TmdbMovieSummary[]> {
  const q = query.trim();

  if (!q) {
    return [];
  }

  const params = new URLSearchParams({
    q,
    page: String(page),
  });

  const response = await fetchJson<TmdbSearchResponse>(
    `${API_V1_BASE}/tmdb/search?${params.toString()}`
  );

  return response.results ?? [];
}

export async function importTmdbMovieToCatalog(
  tmdbId: number,
): Promise<ImportedMovieResponse> {
  return fetchJson<ImportedMovieResponse>(
    `${API_V1_BASE}/movies/import/${tmdbId}`,
    { method: 'POST' }
  );
}

export async function getMovieVirtueScores(movieId: number): Promise<VirtueScores> {
  const response = await fetchJson<VirtueScoresResponse>(
    `${API_V1_BASE}/movies/${movieId}/virtue-scores`
  );

  const scores = response.virtue_scores ?? {};
  return {
    wisdom: scores.wisdom ?? 0,
    courage: scores.courage ?? 0,
    humanity: scores.humanity ?? 0,
    justice: scores.justice ?? 0,
    temperance: scores.temperance ?? 0,
    transcendence: scores.transcendence ?? 0,
  };
}

export type ChatRequest = {
  message: string;
  user_id?: number | null;
  model?: string;
  temperature?: number;
  max_tokens?: number;
};

export type ChatResponse = {
  reply: string;
  model: string;
};

export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  return fetchJson<ChatResponse>(`${API_V1_BASE}/chat/completions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
}

export async function getMoviesByIds(ids: number[]): Promise<CatalogMovie[]> {
  if (!ids.length) return [];

  const params = new URLSearchParams({
    ids: ids.join(","),
  });

  return fetchJson<CatalogMovie[]>(
    `${API_V1_BASE}/movies/by-ids?${params.toString()}`
  );
}

function calculateMatchScore(movie: ScoredMovie, traits: TraitOptions): number {
  const vals: number[] = [];
  if (traits.Wisdom) vals.push(movie.Wisdom ?? 0);
  if (traits.Courage) vals.push(movie.Courage ?? 0);
  if (traits.Humanity) vals.push(movie.Humanity ?? 0);
  if (traits.Justice) vals.push(movie.Justice ?? 0);
  if (traits.Temperance) vals.push(movie.Temperance ?? 0);
  if (traits.Transcendence) vals.push(movie.Transcendence ?? 0);

  if (vals.length === 0) return 0;
  return Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 100);
}

// export async function getTopMoviesByTraits(
//   traits: TraitOptions
// ): Promise<ScoredMovie[]> {

//   const hasEnabledTraits = Object.values(traits).some(Boolean);
//   console.log(hasEnabledTraits);
//   if (!hasEnabledTraits) return [];

//   const movies = await fetchJson<CatalogMovie[]>(`${API_V1_BASE}/movies?skip=0&limit=100`);

//   const scoredMovies = await Promise.all(
//     movies.map(async (movie) => {
//       let virtueScores: VirtueScoresResponse['virtue_scores'] = {};

//       try {
//         const scoresResponse = await fetchJson<VirtueScoresResponse>(
//           `${API_V1_BASE}/movies/${movie.id}/virtue-scores`
//         );
//         virtueScores = scoresResponse.virtue_scores ?? {};
//       } catch {
//         virtueScores = {};
//       }

//       const mappedMovie: ScoredMovie = {
//         id: movie.id,
//         title: movie.title,
//         summary: movie.summary ?? '',
//         image_url: movie.image_url ?? '',
//         vote_average: movie.vote_average ?? null,
//         release_date: movie.release_date ?? '',
//         adult: movie.adult ? 1 : 0,
//         match_score: 0,
//         Humanity: virtueScores.humanity ?? 0,
//         Wisdom: virtueScores.wisdom ?? 0,
//         Courage: virtueScores.courage ?? 0,
//         Temperance: virtueScores.temperance ?? 0,
//         Transcendence: virtueScores.transcendence ?? 0,
//         Justice: virtueScores.justice ?? 0,
//       };

//       return {
//         ...mappedMovie,
//         match_score: calculateMatchScore(mappedMovie, traits),
//       };
//     })
//   );

//   return scoredMovies.sort((a, b) => b.match_score - a.match_score).slice(0, 20);
// }
export async function getTopMoviesByTraits(
  traits: TraitOptions,
  excludeIds: number[] = []
): Promise<CatalogMovie[]> {

  const hasEnabledTraits = Object.values(traits).some(Boolean);
  // If nothing is selected, treat everything as enabled
  const effectiveTraits: TraitOptions = hasEnabledTraits
    ? traits
    : {
        Wisdom: true,
        Courage: true,
        Humanity: true,
        Justice: true,
        Temperance: true,
        Transcendence: true,
      };
      
  const query = new URLSearchParams({
    wisdom: effectiveTraits.Wisdom ? "1" : "0",
    courage: effectiveTraits.Courage ? "1" : "0",
    humanity: effectiveTraits.Humanity ? "1" : "0",
    justice: effectiveTraits.Justice ? "1" : "0",
    temperance: effectiveTraits.Temperance ? "1" : "0",
    transcendence: effectiveTraits.Transcendence ? "1" : "0",
    rating_weight: "0.4",
    limit: "20",
  });

  if (excludeIds.length > 0) {
    query.append("exclude_ids", excludeIds.join(","))
  }

  const movies = await fetchJson<CatalogMovie[]>(
    `${API_V1_BASE}/movies/recommend?${query.toString()}`
  );

  

  return movies;
}