import ParallaxScrollView from "@/components/parallax-scroll-view";
import { ThemedText } from "@/components/themed-text";
import { ThemedView } from "@/components/themed-view";
//import { MovieCatalogue } from "@/constants/dummycatalogue";
import { globalStyles } from "@/constants/globalStyles";
import { Image } from "expo-image";
import { useEffect, useState } from 'react';
import {
  FlatList,
  Modal,
  Pressable, StyleSheet, Text, TouchableOpacity, View
} from "react-native";
import tinycolor from "tinycolor2";
import { getTopMoviesByTraits, initDb, ScoredMovie, TraitOptions } from "../../src/db/database";

// type DbMovie = {
//   id: number;
//   title: string;
//   poster:string,
//   year: number;
//   rating: number;
//   genre: string;
//   humanity: number;
//   courage: number;
//   justice: number;
//   purpose: number;
//   restraint: number;
//   wisdom: number;
// };

// type Trait =
//   | "humanity"
//   | "courage"
//   | "justice"
//   | "purpose"
//   | "restraint"
//   | "wisdom";

// function computeScore(movie: any, activeTraits: TraitOptions[]): number {
//   if (activeTraits.length === 0) return 0;

//   const sum = activeTraits.reduce((acc, trait) => {
//     return acc + (movie[trait] ?? 0);
//   }, 0)

//   return sum/ activeTraits.length
// }
//const movies: Movie[] = MovieCatalogue;

/**
 * RecommendedMovie wraps a catalogue movie with a computed recommendation score.
 * When the real engine is ready, replace `recommendationScore` with the actual
 * output and remove the dummy generation below.
 */
type RecommendedMovie = ScoredMovie & {
  recommendationScore: number | null; // 0–100, null = not yet computed
};

/**
 * Generates a fake recommendation score for a movie.
 * REPLACE THIS with the real recommendation engine output.
 * Kept deterministic (seeded by id) so the list doesn't shuffle on re-render.
 */
// function getDummyRecommendationScore(id: string): number {
//   // Simple deterministic hash: sum of char codes mod 100, mapped to 40–99
//   const hash = id.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0);
//   return 40 + (hash % 60);
// }

/**
 * Attaches dummy scores and placeholder IMDb ratings to catalogue movies.
 * REPLACE this function's body with a real data-fetching call when ready.
 */
function buildRecommendedList(catalogue: ScoredMovie[]): RecommendedMovie[] {
  return catalogue.map((movie) => ({
    ...movie,
    vote_average: movie.vote_average ?? null
  }));
}

/** Maps a 0–100 recommendation score to a colour. */
function scoreColor(score: number): string {
  if (score >= 80) return "#4caf50";
  if (score >= 60) return "#ff9800";
  return "#f44336";
}


export default function HomeScreen() {

  function openInfoOverlay(movie: ScoredMovie) {
    setSelectedMovie(movie);
    setOverlayVisible(true);
  }

  function closeInfoOverlay() {
    setOverlayVisible(false);
    setSelectedMovie(null);
  }

  const [selectedMovie, setSelectedMovie] = useState<ScoredMovie | null>(null);
  const [overlayVisible, setOverlayVisible] = useState(false);

  const [toggles, setToggles] = useState({
    Wisdom: { state: false, deactColor: "#457", actColor: "#9af" },
    Humanity: { state: false, deactColor: "#172", actColor: "#2e4" },
    Purpose: { state: false, deactColor: "#662", actColor: "#cc4" },
    Justice: { state: false, deactColor: "#526", actColor: "#a4e" },
    Restraint: { state: false, deactColor: "#445", actColor: "#88a" },
    Courage: { state: false, deactColor: "#751", actColor: "#fa2" },
  });

  const [scoredMovies, setDbMovies] = useState<ScoredMovie[]>([]);

  const activeTraits: TraitOptions = Object.entries(toggles).reduce(
    (acc, [key, value]) => {
      if (value.state) {
        acc[key as keyof TraitOptions] = true;
      }
      return acc;
    },
    {} as TraitOptions
  );

useEffect(() => {
  initDb();

  const movies = getTopMoviesByTraits(activeTraits);
  setDbMovies(movies);
}, [activeTraits]);



  // const enrichedMovies = ScoredMovies.map((m) => ({
  //   ...m,
  //   recommendationScore: computeScore(m, activeTraits),
  // }));


  const sortedMovies = [...scoredMovies].sort(
    (a,b) => b.match_score - a.match_score
  );

  // Build the full recommended list once (replace with useMemo + real fetch later)
  const allRecommendedMovies: RecommendedMovie[] = buildRecommendedList(scoredMovies);

  // Filter by active category toggles; show all when none are active
  // const filteredMovies: RecommendedMovie[] =
  //   activeCategories.length === 0
  //     ? allRecommendedMovies
  //     : allRecommendedMovies.filter((movie) =>
  //         movie.categories.some((cat) => activeCategories.includes(cat))
  //       );

  // // Sort by recommendation score descending (nulls last)
  // const sortedMovies = [...filteredMovies].sort((a, b) => {
  //   if (a.recommendationScore === null) return 1;
  //   if (b.recommendationScore === null) return -1;
  //   return b.recommendationScore - a.recommendationScore;
  // });

  function toggle(key: keyof typeof toggles) {
    console.log(activeTraits);
    setToggles((prev) => ({
      ...prev,
      [key]: {
        ...prev[key],
        state: !prev[key].state,
      },
    }));
  }

  console.log(activeTraits);
  

  return (
    <>
    <Modal
      visible={overlayVisible}
      transparent={true}
      animationType="fade"
      onRequestClose={closeInfoOverlay}
    >
      <View style={styles.modalBackdrop}>
        <View style={styles.modalContent}>
          {selectedMovie && (
            <>
              <Image
                source={{ uri: selectedMovie.image_url }}
                style={styles.modalPoster}
              />

              <Text style={styles.modalTitle}>
                {selectedMovie.title}
              </Text>

              <Text style={styles.modalYear}>
                {selectedMovie.release_date}
              </Text>

              <Text style={styles.modalRating}>
                IMDb: {selectedMovie.vote_average}/10
              </Text>

              <View style={styles.traitsContainer}>
                <Text>Humanity: {selectedMovie.Humanity}</Text>
                <Text>Courage: {selectedMovie.Courage}</Text>
                <Text>Justice: {selectedMovie.Justice}</Text>
                <Text>Transcendence: {selectedMovie.Transcendence}</Text>
                <Text>Temperance: {selectedMovie.Temperance}</Text>
                <Text>Wisdom: {selectedMovie.Wisdom}</Text>
              </View>

              <TouchableOpacity
                style={styles.closeButton}
                onPress={closeInfoOverlay}
              >
                <Text style={styles.closeButtonText}>Close</Text>
              </TouchableOpacity>
            </>
          )}
        </View>
      </View>
    </Modal>
    <ParallaxScrollView
      headerBackgroundColor={{ light: "#A1CEDC", dark: "#1D3D47" }}
      headerImage={
        <Image
          source={require("@/assets/images/partial-react-logo.png")}
          style={styles.reactLogo}
        />
      }
    >
      <ThemedView style={styles.titleContainer}>
        <ThemedText type="title">EudAImonic Movie Recommender</ThemedText>
      </ThemedView>

      {/* Category filter toggles */}
      <View style={styles.buttonContainer}>
        {Object.entries(toggles).map(([key, value]) => {
          const bg = value.state
            ? value.actColor
            : tinycolor(value.actColor).desaturate(50).toHexString();
          return (
            <Pressable
              key={key}
              onPress={() => toggle(key as keyof typeof toggles)}
              style={({ pressed }) => [
                styles.button,
                { backgroundColor: bg },

                // active = 'popped out'
                value.state && styles.active,

                // pressed = slight push-in feedback
                pressed && styles.pressed,
              ]}
            >
              <Text style={styles.text}>
                {key} {value ? "" : ""}
              </Text>
            </Pressable>
          );
        })}
      </View>

      {/* <View style={{ marginTop: 20 }}>
        {filteredMovies.map((movie) => (
          <View key={movie.id} style={styles.movieItem}>
            <Text>{movie.title}</Text>
          </View>
        ))}
      </View> */}

      <FlatList
        data={sortedMovies}
        windowSize={5}
        initialNumToRender={8}
        maxToRenderPerBatch={6}
        removeClippedSubviews={true}
        keyExtractor={(item) => item.id.toString()}
        scrollEnabled={false} // disable internal scrolling to let ParallaxScrollView handle it
        contentContainerStyle={globalStyles.listContent}
        renderItem={({ item, index }) => (
          <TouchableOpacity 
          
          style={globalStyles.movieItemContainer}
          activeOpacity={0.7}
          onPress={() => openInfoOverlay(item)}  // wire up when ready
          >
            <ThemedView style={globalStyles.movieItem}>
              {/* Rank Badge */}
              <View style={styles.rankBadge}>
                <ThemedText style={styles.rankText}>#{index + 1}</ThemedText>
              </View>

              {/* Movie Info + Poster*/}
              <ThemedView style={globalStyles.movieContent}>
                <ThemedView style={globalStyles.posterPlaceholder}>
                  <Image source={{ uri: item.image_url }} style={styles.modalPoster} />
                </ThemedView>
                <ThemedView style={globalStyles.movieInfo}>
                  <ThemedText type="subtitle" numberOfLines={1} ellipsizeMode="tail">
                    {item.title}
                  </ThemedText>
                  {/* IMDb rating row */}
                  <View style={styles.imdbRow}>
                    <Text style={styles.imdbLabel}>IMDb</Text>
                    <Text style={styles.imdbValue}>
                      {item.vote_average !== null ? `${item.vote_average}/10` : "—"}
                    </Text>
                  </View>
                </ThemedView>
              </ThemedView>
              {/* Recommendation score column */}
              <View style={styles.scoreSection}>
                <ThemedText style={styles.scoreLabel}>Match</ThemedText>
                {item.match_score !== null ? (
                  <>
                    <ThemedText
                      style={[
                        styles.scoreValue,
                        { color: scoreColor(item.match_score) },
                      ]}
                    >
                      {item.match_score}%
                    </ThemedText>
                    {/* Visual bar */}
                    <View style={styles.scoreBarTrack}>
                      <View
                        style={[
                          styles.scoreBarFill,
                          {
                            width: `${item.match_score}%`,
                            backgroundColor: scoreColor(item.match_score),
                          },
                        ]}
                      />
                    </View>
                  </>
                ) : (
                  <ThemedText style={styles.scoreValue}>—</ThemedText>
                )}
              </View>
            </ThemedView>
          </TouchableOpacity>
        )}
      />
    </ParallaxScrollView>
    </>
  );
}

const styles = StyleSheet.create({
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.7)",
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
  },

  modalContent: {
    width: "100%",
    maxWidth: 400,
    backgroundColor: "#222",
    borderRadius: 16,
    padding: 20,
    alignItems: "center",
  },

  modalPoster: {
    width: 180,
    height: 270,
    borderRadius: 12,
    marginBottom: 16,
  },

  modalTitle: {
    fontSize: 22,
    fontWeight: "bold",
    color: "white",
    textAlign: "center",
  },

  modalYear: {
    color: "#bbb",
    marginTop: 4,
  },

  modalRating: {
    color: "#f5c518",
    marginTop: 8,
    fontSize: 16,
  },

  traitsContainer: {
    marginTop: 20,
    gap: 6,
    width: "100%",
  },

  closeButton: {
    marginTop: 24,
    backgroundColor: "#444",
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 10,
  },

  closeButtonText: {
    color: "white",
    fontWeight: "600",
  },
  // Layout + Header
  titleContainer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  stepContainer: {
    gap: 8,
    marginBottom: 8,
  },
  reactLogo: {
    height: 178,
    width: 290,
    bottom: 0,
    left: 0,
    position: "absolute",
  },

  // Category filter buttons
  buttonContainer: {
    flexDirection: "row",
    flexWrap: "wrap",
    padding: 16,
  },
  button: {
    width: "45%",
    margin: "1.5%",
    padding: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: "transparent",
    alignItems: "center",

    // base (flat)
    elevation: 2, // Android
    shadowColor: "#000", // iOS
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 3,
  },

  active: {
    // lifted look
    elevation: 8,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.35,
    shadowRadius: 6,

    // subtle scale up
    transform: [{ scale: 1.05 }],

    // optional: outline
    borderWidth: 2,
    borderColor: "#fff",
  },

  pressed: {
    // quick press feedback (push in)
    transform: [{ scale: 0.97 }],
    opacity: 0.85,
  },

  text: {
    color: "black",
  },

  // Movie list Items
  movieItem: {
    padding: 12,
    marginBottom: 8,
    backgroundColor: "#222",
    borderRadius: 8,
  },

  rankBadge: {
    width: 28,
    alignItems: "center",
    flexShrink: 0,
  },
  rankText: {
    fontSize: 11,
    opacity: 0.5,
    fontWeight: "600",
  },
  imdbRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    marginTop: 2,
  },
  imdbLabel: {
    fontSize: 10,
    fontWeight: "700",
    color: "#f5c518",       // IMDb yellow — intentional hardcode
    letterSpacing: 0.5,
  },
  imdbValue: {
    fontSize: 12,
    color: "#f5c518",
    fontWeight: "500",
  },

  // Recommendation score column
  scoreSection: {
    alignItems: "center",
    paddingHorizontal: 8,
    width: 70,
    height: "100%",
    justifyContent: "center",
    gap: 4,
  },
  scoreLabel: {
    fontSize: 11,
    opacity: 0.6,
    letterSpacing: 0.5,
  },
  scoreValue: {
    fontSize: 16,
    fontWeight: "bold",
  },
  scoreBarTrack: {
    width: 48,
    height: 4,
    borderRadius: 2,
    backgroundColor: "rgba(255,255,255,0.15)",
    overflow: "hidden",
  },
  scoreBarFill: {
    height: "100%",
    borderRadius: 2,
  },
});
