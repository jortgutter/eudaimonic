import ParallaxScrollView from "@/components/parallax-scroll-view";
import { ThemedText } from "@/components/themed-text";
import { ThemedView } from "@/components/themed-view";
import { Image } from "expo-image";
import { useEffect, useState } from 'react';
import {
  Modal,
  Pressable, StyleSheet, Text, TouchableOpacity, View
} from "react-native";
import { getTopMoviesByTraits, ScoredMovie, TraitOptions } from "../../src/db/database";

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


/** Maps a 0–100 recommendation score to a colour. */
function scoreColor(score: number): string {
  if (score >= 80) return "#4caf50";
  if (score >= 60) return "#ff9800";
  return "#f44336";
}

const TraitBar = ({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) => {
  const clamped = Math.max(0, Math.min(1, value ?? 0));

  return (
    <View style={{ marginBottom: 8 }}>
      <Text style={{ marginBottom: 4 }}>
        {label}: {clamped.toFixed(2)}
      </Text>

      <View
        style={{
          height: 8,
          width: "100%",
          backgroundColor: "#333",
          borderRadius: 4,
          overflow: "hidden",
        }}
      >
        <View
          style={{
            height: "100%",
            width: `${clamped * 100}%`,
            backgroundColor: color,
          }}
        />
      </View>
    </View>
  );
};

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
    Transcendence: { state: false, deactColor: "#662", actColor: "#cc4" },
    Justice: { state: false, deactColor: "#526", actColor: "#a4e" },
    Temperance: { state: false, deactColor: "#445", actColor: "#88a" },
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
  let cancelled = false;

  (async () => {
    try {
      const movies = await getTopMoviesByTraits(activeTraits);
      if (!cancelled) {
        // Log how many movies were loaded to help debug rendering on devices
         
        console.log('Loaded top movies count:', movies.length, movies.slice(0,3).map(m=>m.title));
        setDbMovies(movies);
      }
    } catch (error) {
      console.error("Failed to load movies from backend", error);
      if (!cancelled) {
        setDbMovies([]);
      }
    }
  })();

  return () => {
    cancelled = true;
  };
}, [activeTraits]);



  // const enrichedMovies = ScoredMovies.map((m) => ({
  //   ...m,
  //   recommendationScore: computeScore(m, activeTraits),
  // }));


  const sortedMovies = [...scoredMovies].sort(
    (a,b) => b.match_score - a.match_score
  );

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
                <TraitBar
                  label="Humanity"
                  value={selectedMovie.Humanity}
                  color={toggles.Humanity.actColor}
                />
                <TraitBar
                  label="Courage"
                  value={selectedMovie.Courage}
                  color={toggles.Courage.actColor}
                />
                <TraitBar
                  label="Justice"
                  value={selectedMovie.Justice}
                  color={toggles.Justice.actColor}
                />
                <TraitBar
                  label="Temperance"
                  value={selectedMovie.Temperance}
                  color={toggles.Temperance.actColor}
                />
                <TraitBar
                  label="Transcendence"
                  value={selectedMovie.Transcendence}
                  color={toggles.Transcendence.actColor}
                />
                <TraitBar
                  label="Wisdom"
                  value={selectedMovie.Wisdom}
                  color={toggles.Wisdom.actColor}
                />
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
            : value.deactColor;
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

      <View style={styles.recommendationsSection}>
        <View style={styles.recommendationsHeader}>
          <View>
            <ThemedText type="subtitle">Recommendations</ThemedText>
            <Text style={styles.recommendationsSubtext}>
              {sortedMovies.length} matching movies
            </Text>
          </View>

          <View style={styles.recommendationsPill}>
            <Text style={styles.recommendationsPillText}>
              {Object.entries(toggles).filter(([, value]) => value.state).length} virtues used
            </Text>
          </View>
        </View>

        {sortedMovies.length === 0 ? (
          <View style={styles.emptyState}>
            <Text style={styles.emptyStateTitle}>Choose a virtue</Text>
            <Text style={styles.emptyStateText}>
              Tap one or more virtues above to load movie recommendations.
            </Text>
          </View>
        ) : (
          <View style={styles.recommendationList}>
            {sortedMovies.map((item, index) => (
              <TouchableOpacity
                key={item.id}
                style={styles.recommendationCard}
                activeOpacity={0.85}
                onPress={() => openInfoOverlay(item)}
              >
                <View style={styles.cardPosterWrap}>
                  <Image source={{ uri: item.image_url }} style={styles.cardPoster} />
                  <View style={styles.cardRankBadge}>
                    <Text style={styles.cardRankText}>#{index + 1}</Text>
                  </View>
                </View>

                <View style={styles.cardBody}>
                  <View style={styles.cardTopRow}>
                    <ThemedText type="subtitle" numberOfLines={2}>
                      {item.title}
                    </ThemedText>
                    <View style={styles.matchPill}>
                      <Text style={[styles.matchPillText, { color: scoreColor(item.match_score) }]}>
                        {item.match_score}%
                      </Text>
                    </View>
                  </View>

                  <Text style={styles.cardMeta}>
                    IMDb {item.vote_average !== null ? `${item.vote_average}/10` : "—"}
                    {item.release_date ? ` • ${item.release_date}` : ""}
                  </Text>

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
                </View>
              </TouchableOpacity>
            ))}
          </View>
        )}
      </View>
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
  listPoster: {
    width: "100%",
    height: "100%",
    borderRadius: 4,
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

  recommendationsSection: {
    gap: 12,
  },
  recommendationsHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  recommendationsSubtext: {
    marginTop: 4,
    opacity: 0.7,
    fontSize: 12,
  },
  recommendationsPill: {
    backgroundColor: "rgba(255,255,255,0.1)",
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  recommendationsPillText: {
    fontSize: 12,
    fontWeight: "600",
  },
  emptyState: {
    paddingVertical: 28,
    paddingHorizontal: 18,
    borderRadius: 16,
    backgroundColor: "rgba(255,255,255,0.08)",
    gap: 8,
  },
  emptyStateTitle: {
    fontSize: 16,
    fontWeight: "700",
  },
  emptyStateText: {
    opacity: 0.75,
    lineHeight: 20,
  },
  recommendationList: {
    gap: 12,
  },
  recommendationCard: {
    flexDirection: "row",
    gap: 12,
    padding: 12,
    borderRadius: 16,
    backgroundColor: "rgba(255,255,255,0.1)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
  },
  cardPosterWrap: {
    width: 72,
    height: 108,
    borderRadius: 12,
    overflow: "hidden",
    backgroundColor: "rgba(255,255,255,0.08)",
  },
  cardPoster: {
    width: "100%",
    height: "100%",
  },
  cardRankBadge: {
    position: "absolute",
    top: 8,
    left: 8,
    backgroundColor: "rgba(0,0,0,0.75)",
    borderRadius: 999,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  cardRankText: {
    color: "white",
    fontSize: 10,
    fontWeight: "700",
  },
  cardBody: {
    flex: 1,
    gap: 8,
    justifyContent: "center",
  },
  cardTopRow: {
    gap: 8,
  },
  matchPill: {
    alignSelf: "flex-start",
    backgroundColor: "rgba(255,255,255,0.12)",
    borderRadius: 999,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  matchPillText: {
    fontSize: 12,
    fontWeight: "700",
  },
  cardMeta: {
    opacity: 0.75,
    fontSize: 12,
  },
  scoreBarTrack: {
    width: "100%",
    height: 6,
    borderRadius: 999,
    backgroundColor: "rgba(255,255,255,0.15)",
    overflow: "hidden",
  },
  scoreBarFill: {
    height: "100%",
    borderRadius: 999,
  },
});
