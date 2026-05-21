

const DEFAULT_HOST = 'http://145.116.129.10:8000';

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

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, init);
  } catch (err) {
    const msg = `Network error when fetching ${url}: ${err}`;
     
    console.error(msg);
    throw new Error(msg);
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
  traits: TraitOptions
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

  const movies = await fetchJson<CatalogMovie[]>(
    `${API_V1_BASE}/movies/recommend?${query.toString()}`
  );

  return movies;
}