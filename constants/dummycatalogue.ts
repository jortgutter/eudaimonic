// Movie catalogue - this will eventually come from an API/database
export const MovieCatalogue = [
  {
    id: "1",
    title: "Princess Mononoke",
    year: 1997,
    duration: "2h 13m",
    poster: "placeholder",
    categories: ["Courage", "Wisdom"],
    imdbRating: 8.3,
    Director: "Hayao Miyazaki",
    stars: ["Yôji Matsuda", "Yuriko Ishida", "Yûko Tanaka"],
    
  },
  {
    id: "2",
    title: "Iron Man",
    year: 2008,
    duration: "2h 6m",
    poster: "placeholder",
    categories: ["Courage", "Wisdom"],
    imdbRating: 7.9,
    Director: "Jon Favreau",
    stars: ["Robert Downey Jr.", "Terrence Howard", "Gwyneth Paltrow"],
  },
  {
    id: "3",
    title: "Up",
    year: 2009,
    duration: "1h 36m",
    poster: "placeholder",
    categories: ["Humanity"],
    imdbRating: 8.3,
    Director: ["Pete Docter", "Bob Peterson"],
    stars: ["John Ratzenberger", "Jordan Nagai", "Edward Asner"],
  },
];

export function extractMovieDisplayInfo(catalogueMovie: any) {
  return {
    id: catalogueMovie.id,
    title: catalogueMovie.title,
    poster: catalogueMovie.poster,
    categories: catalogueMovie.categories,
    imdbRating: catalogueMovie.imdbRating,
    Director: catalogueMovie.Director,
    stars: catalogueMovie.stars,
    year: catalogueMovie.year,
    duration: catalogueMovie.duration,
  };
}