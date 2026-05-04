// Movie catalogue - this will eventually come from an API/database
export const MovieCatalogue = [
  {
    id: "1",
    title: "Princess Mononoke",
    poster: "placeholder",
    categories: ["Courage", "Wisdom"],
  },
  {
    id: "2",
    title: "Iron Man",
    poster: "placeholder",
    categories: ["Courage", "Wisdom"],
  },
  {
    id: "3",
    title: "Up",
    poster: "placeholder",
    categories: ["Humanity"],
  },
];

export function extractMovieDisplayInfo(catalogueMovie: any) {
  return {
    id: catalogueMovie.id,
    title: catalogueMovie.title,
    poster: catalogueMovie.poster,
    categories: catalogueMovie.categories,
  };
}