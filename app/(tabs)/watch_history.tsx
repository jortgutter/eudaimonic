import { Image } from "expo-image";
import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Modal,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { ThemedText } from "@/components/themed-text";
import { ThemedView } from "@/components/themed-view";
import { globalStyles } from "@/constants/globalStyles";
import {
  CatalogMovie,
  getCatalogMovies,
  getMovieVirtueScores,
  VirtueScores,
} from "../../src/db/database";
import { loadUserInfo, saveUserInfo } from "../../src/storage/userinfo";

type RatingsMap = Record<string, number>;

const EMPTY_VIRTUE_SCORES: VirtueScores = {
  wisdom: 0,
  courage: 0,
  humanity: 0,
  justice: 0,
  temperance: 0,
  transcendence: 0,
};

const VIRTUE_META: Array<{ key: keyof VirtueScores; label: string; color: string }> = [
  { key: "wisdom", label: "Wisdom", color: "#4A90E2" },
  { key: "courage", label: "Courage", color: "#F5A623" },
  { key: "humanity", label: "Humanity", color: "#7ED321" },
  { key: "justice", label: "Justice", color: "#BD10E0" },
  { key: "temperance", label: "Temperance", color: "#50E3C2" },
  { key: "transcendence", label: "Transcendence", color: "#E94E77" },
];

const VIRTUE_COLUMNS = [VIRTUE_META.slice(0, 3), VIRTUE_META.slice(3, 6)];

function toPercent(value: number): number {
  const raw = value <= 1 ? value * 100 : value;
  return Math.max(0, Math.min(100, Math.round(raw)));
}

export default function WatchHistoryScreen() {
  const [catalogMovies, setCatalogMovies] = useState<CatalogMovie[]>([]);
  const [watchedMovieIds, setWatchedMovieIds] = useState<number[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [ratings, setRatings] = useState<RatingsMap>({});
  const [openMenuId, setOpenMenuId] = useState<number | null>(null);
  const [menuPosition, setMenuPosition] = useState({ x: 0, y: 0 });
  const [showRatingOverlay, setShowRatingOverlay] = useState(false);
  const [selectedMovieForRating, setSelectedMovieForRating] = useState<CatalogMovie | null>(null);
  const [showInfoOverlay, setShowInfoOverlay] = useState(false);
  const [selectedMovieForInfo, setSelectedMovieForInfo] = useState<CatalogMovie | null>(null);
  const [selectedMovieVirtues, setSelectedMovieVirtues] = useState<VirtueScores>(EMPTY_VIRTUE_SCORES);
  const [isVirtueLoading, setIsVirtueLoading] = useState(false);
  const [watchHistorySearchQuery, setWatchHistorySearchQuery] = useState("");
  const [addMovieSearchQuery, setAddMovieSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    (async () => {
      try {
        const [movies, userInfo] = await Promise.all([getCatalogMovies(100), loadUserInfo()]);

        if (!mounted) return;

        setCatalogMovies(movies);
        setWatchedMovieIds(userInfo.watchedMovieIds);
        setRatings(userInfo.ratings);
      } catch (error) {
        console.error("Failed to load watch history data", error);
        if (!mounted) return;
        setLoadError("Could not load movies from backend.");
      } finally {
        if (mounted) setIsLoading(false);
      }
    })();

    return () => {
      mounted = false;
    };
  }, []);

  const watchedMovies = useMemo(() => {
    const watchedSet = new Set(watchedMovieIds);
    return catalogMovies.filter((movie) => watchedSet.has(movie.id));
  }, [catalogMovies, watchedMovieIds]);

  const availableMovies = useMemo(() => {
    const watchedSet = new Set(watchedMovieIds);
    return catalogMovies.filter((movie) => !watchedSet.has(movie.id));
  }, [catalogMovies, watchedMovieIds]);

  async function persistUserInfo(nextIds: number[], nextRatings: RatingsMap) {
    await saveUserInfo({ watchedMovieIds: nextIds, ratings: nextRatings });
  }

  const searchMovies = (movies: CatalogMovie[], query: string): CatalogMovie[] => {
    if (!query.trim()) return movies;

    const lowerQuery = query.toLowerCase();
    return movies.filter((movie) => {
      const titleMatch = movie.title.toLowerCase().includes(lowerQuery);
      const genreMatch = (movie.genres ?? []).some((genre) =>
        genre.toLowerCase().includes(lowerQuery)
      );
      return titleMatch || genreMatch;
    });
  };

  const openMenu = (movieId: number, event: any) => {
    const { pageX, pageY } = event.nativeEvent;
    setMenuPosition({ x: pageX, y: pageY });
    setOpenMenuId(movieId);
  };

  const addMovieFromCatalogue = async (catalogueMovie: CatalogMovie) => {
    const nextIds = Array.from(new Set([...watchedMovieIds, catalogueMovie.id]));
    setWatchedMovieIds(nextIds);
    await persistUserInfo(nextIds, ratings);
    setShowAddModal(false);
  };

  const deleteMovie = async (movieId: number) => {
    const nextIds = watchedMovieIds.filter((id) => id !== movieId);
    setWatchedMovieIds(nextIds);
    await persistUserInfo(nextIds, ratings);
    setOpenMenuId(null);
  };

  const openRatingOverlay = (movie: CatalogMovie) => {
    setSelectedMovieForRating(movie);
    setShowRatingOverlay(true);
    setOpenMenuId(null);
  };

  const rateMovie = async (score: number) => {
    if (!selectedMovieForRating) return;

    const nextRatings = { ...ratings, [selectedMovieForRating.id]: score };
    setRatings(nextRatings);
    await persistUserInfo(watchedMovieIds, nextRatings);
    setShowRatingOverlay(false);
    setSelectedMovieForRating(null);
  };

  const openInfoOverlay = async (movie: CatalogMovie) => {
    setSelectedMovieForInfo(movie);
    setShowInfoOverlay(true);
    setOpenMenuId(null);

    setIsVirtueLoading(true);
    try {
      const scores = await getMovieVirtueScores(movie.id);
      setSelectedMovieVirtues(scores);
    } catch (error) {
      console.error("Failed to load virtue scores", error);
      setSelectedMovieVirtues(EMPTY_VIRTUE_SCORES);
    } finally {
      setIsVirtueLoading(false);
    }
  };

  const handleCloseAddModal = () => {
    setShowAddModal(false);
    setAddMovieSearchQuery("");
  };

  if (isLoading) {
    return (
      <ThemedView style={styles.container}>
        <ActivityIndicator size="large" />
        <ThemedText>Loading movies...</ThemedText>
      </ThemedView>
    );
  }

  return (
    <ThemedView style={styles.container}>
      <ThemedText type="title">Watch History</ThemedText>
      <ThemedText type="subtitle">You can view your watched movies here.</ThemedText>
      {loadError ? <ThemedText>{loadError}</ThemedText> : null}

      <TextInput
        placeholder="Search movies..."
        value={watchHistorySearchQuery}
        style={styles.searchBar}
        onChangeText={(text) => setWatchHistorySearchQuery(text)}
      />

      <FlatList
        data={searchMovies(watchedMovies, watchHistorySearchQuery)}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={globalStyles.listContent}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={globalStyles.movieItemContainer}
            onPress={() => openInfoOverlay(item)}
            activeOpacity={0.7}
          >
            <ThemedView style={globalStyles.movieItem}>
              <TouchableOpacity style={styles.menuButton} onPress={(e) => openMenu(item.id, e)}>
                <ThemedText style={globalStyles.menuIcon}>⋮</ThemedText>
              </TouchableOpacity>

              <ThemedView style={globalStyles.movieContent}>
                <ThemedView style={globalStyles.posterPlaceholder}>
                  {item.image_url ? (
                    <Image source={{ uri: item.image_url }} style={styles.posterImage} />
                  ) : (
                    <ThemedText>Poster</ThemedText>
                  )}
                </ThemedView>
                <ThemedView style={globalStyles.movieInfo}>
                  <ThemedText type="subtitle" numberOfLines={1} ellipsizeMode="tail">
                    {item.title}
                  </ThemedText>
                  <ThemedText style={globalStyles.categories} numberOfLines={1} ellipsizeMode="tail">
                    {(item.genres ?? []).join(", ") || "No genres"}
                  </ThemedText>
                </ThemedView>
              </ThemedView>

              <TouchableOpacity style={styles.ratingSection} onPress={() => openRatingOverlay(item)}>
                <ThemedText style={styles.ratingLabel}>Rating</ThemedText>
                <ThemedText style={styles.ratingValue}>
                  {ratings[item.id] ? `${ratings[item.id]}/10` : "Not rated"}
                </ThemedText>
              </TouchableOpacity>
            </ThemedView>
          </TouchableOpacity>
        )}
      />

      <TouchableOpacity style={styles.fab} onPress={() => setShowAddModal(true)}>
        <ThemedText style={globalStyles.fabText}>+</ThemedText>
      </TouchableOpacity>

      <Modal
        visible={showAddModal}
        animationType="slide"
        transparent={false}
        onRequestClose={() => setShowAddModal(false)}
      >
        <ThemedView style={styles.modalContainer}>
          <ThemedText type="title" style={styles.modalTitle}>
            Add Movie to History
          </ThemedText>
          <TextInput
            placeholder="Search movies..."
            value={addMovieSearchQuery}
            style={styles.searchBar}
            onChangeText={(text) => setAddMovieSearchQuery(text)}
          />
          <FlatList
            data={searchMovies(availableMovies, addMovieSearchQuery)}
            keyExtractor={(item) => item.id.toString()}
            contentContainerStyle={globalStyles.modalListContent}
            renderItem={({ item }) => (
              <TouchableOpacity style={styles.movieSelectItem} onPress={() => addMovieFromCatalogue(item)}>
                <ThemedView style={globalStyles.posterPlaceholder}>
                  {item.image_url ? (
                    <Image source={{ uri: item.image_url }} style={styles.posterImage} />
                  ) : (
                    <ThemedText>Poster</ThemedText>
                  )}
                </ThemedView>
                <ThemedView style={globalStyles.movieInfo}>
                  <ThemedText type="subtitle">{item.title}</ThemedText>
                  <ThemedText style={globalStyles.categories}>
                    {(item.genres ?? []).join(", ") || "No genres"}
                  </ThemedText>
                </ThemedView>
              </TouchableOpacity>
            )}
          />
          <TouchableOpacity style={styles.closeButton} onPress={handleCloseAddModal}>
            <ThemedText style={globalStyles.infoCloseButtonText}>Close</ThemedText>
          </TouchableOpacity>
        </ThemedView>
      </Modal>

      <Modal
        visible={showRatingOverlay}
        animationType="fade"
        transparent={true}
        onRequestClose={() => setShowRatingOverlay(false)}
      >
        <ThemedView style={globalStyles.overlayContainer}>
          <ThemedView style={styles.overlayContent}>
            <ThemedText type="title" style={globalStyles.overlayTitle}>
              Rate {selectedMovieForRating?.title}
            </ThemedText>
            <ThemedText style={globalStyles.overlayDescription}>Select a rating from 1 to 10</ThemedText>
            <View style={styles.ratingButtonsContainer}>
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((score) => (
                <TouchableOpacity key={score} style={styles.ratingButton} onPress={() => rateMovie(score)}>
                  <ThemedText style={styles.ratingButtonText}>{score}</ThemedText>
                </TouchableOpacity>
              ))}
            </View>
            <TouchableOpacity
              style={globalStyles.overlayCloseButton}
              onPress={() => setShowRatingOverlay(false)}
            >
              <ThemedText style={globalStyles.infoCloseButtonText}>Cancel</ThemedText>
            </TouchableOpacity>
          </ThemedView>
        </ThemedView>
      </Modal>

      <Modal
        visible={showInfoOverlay}
        animationType="slide"
        transparent={false}
        onRequestClose={() => setShowInfoOverlay(false)}
      >
        <ThemedView style={styles.infoContainer}>
          <TouchableOpacity
            style={globalStyles.infoCloseButton}
            onPress={() => setShowInfoOverlay(false)}
          >
            <ThemedText style={globalStyles.infoCloseButtonText}>Close</ThemedText>
          </TouchableOpacity>
          <ThemedText type="title" style={styles.infoTitle}>
            {selectedMovieForInfo?.title}
          </ThemedText>
          <ThemedView style={globalStyles.infoPosterPlaceholder}>
            {selectedMovieForInfo?.image_url ? (
              <Image source={{ uri: selectedMovieForInfo.image_url }} style={styles.infoPosterImage} />
            ) : (
              <ThemedText>Poster</ThemedText>
            )}
          </ThemedView>
          <ThemedText style={globalStyles.infoPlaceholder}>
            {selectedMovieForInfo?.summary || "No summary available."}
          </ThemedText>
          <ThemedText style={globalStyles.infoPlaceholder}>
            {(selectedMovieForInfo?.genres ?? []).join(", ") || "No genres"}
          </ThemedText>
          <ThemedText style={styles.virtueTitle}>Virtue Scores</ThemedText>
          {isVirtueLoading ? (
            <ActivityIndicator size="small" />
          ) : (
            <View style={styles.virtueGrid}>
              {VIRTUE_COLUMNS.map((column, columnIndex) => (
                <View key={columnIndex} style={styles.virtueColumn}>
                  {column.map((virtue) => {
                    const score = toPercent(selectedMovieVirtues[virtue.key]);
                    return (
                      <View key={virtue.key} style={styles.virtueRow}>
                        <View style={styles.virtueRowHeader}>
                          <ThemedText style={styles.virtueLabel}>{virtue.label}</ThemedText>
                          <ThemedText style={styles.virtueValue}>{score}%</ThemedText>
                        </View>
                        <View style={styles.virtueBarTrack}>
                          <View
                            style={[
                              styles.virtueBarFill,
                              { width: `${score}%`, backgroundColor: virtue.color },
                            ]}
                          />
                        </View>
                      </View>
                    );
                  })}
                </View>
              ))}
            </View>
          )}
          {selectedMovieForInfo && ratings[selectedMovieForInfo.id] && (
            <ThemedText style={styles.infoRating}>Your Rating: {ratings[selectedMovieForInfo.id]}/10</ThemedText>
          )}
        </ThemedView>
      </Modal>

      <Modal
        visible={openMenuId !== null}
        animationType="fade"
        transparent={true}
        onRequestClose={() => setOpenMenuId(null)}
      >
        <TouchableOpacity
          style={globalStyles.menuModalOverlay}
          activeOpacity={1}
          onPress={() => setOpenMenuId(null)}
        >
          <ThemedView
            style={[
              globalStyles.menuModalContent,
              { position: "absolute", top: menuPosition.y, left: menuPosition.x },
            ]}
          >
            <TouchableOpacity
              style={globalStyles.menuItem}
              onPress={() => {
                const movie = watchedMovies.find((m) => m.id === openMenuId);
                if (movie) openRatingOverlay(movie);
              }}
            >
              <ThemedText>Rate Movie</ThemedText>
            </TouchableOpacity>
            <TouchableOpacity
              style={globalStyles.menuItem}
              onPress={() => {
                const movie = watchedMovies.find((m) => m.id === openMenuId);
                if (movie) openInfoOverlay(movie);
              }}
            >
              <ThemedText>More Information</ThemedText>
            </TouchableOpacity>
            <TouchableOpacity
              style={[globalStyles.menuItem, styles.deleteMenuItem]}
              onPress={() => { if (openMenuId) deleteMovie(openMenuId); }}
            >
              <ThemedText style={styles.deleteMenuText}>Delete</ThemedText>
            </TouchableOpacity>
          </ThemedView>
        </TouchableOpacity>
      </Modal>
    </ThemedView>
  );
}


const styles = StyleSheet.create({
  // Screen-level layout 
  container: {
    flex: 1,
    padding: 16,
    gap: 16,
  },

  // Search bar (global base + local width constraint)   
  searchBar: {
    ...globalStyles.searchBar,
    width: "35%",
    alignSelf: "center",
  },

  // Menu button (global base + positioning for inside a movie card)
  menuButton: {
    ...globalStyles.menuButton,
    top: 4,
    right: 4,
    zIndex: 10,
  },

  // FAB (global base + fixed size and position)
  fab: {
    ...globalStyles.fab,
    bottom: 20,
    right: 20,
    width: 56,
    height: 56,
  },

  // Rating overlay content box (global base + width cap)
  overlayContent: {
    ...globalStyles.overlayContent,
    maxWidth: 400,
    width: "100%",
  },

  // Rating UI (watch-history specific)
  ratingSection: {
    alignItems: "center",
    paddingHorizontal: 8,
    width: 70,
    height: "100%",
    justifyContent: "center",
  },
  ratingLabel: {
    fontSize: 12,
    opacity: 0.7,
  },
  ratingValue: {
    fontSize: 14,
    fontWeight: "bold",
    marginTop: 2,
  },
  ratingButtonsContainer: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "center",
    gap: 8,
    marginBottom: 20,
  },
  ratingButton: {
    width: "20%",
    aspectRatio: 1,
    backgroundColor: "#007AFF",
    borderRadius: 8,
    justifyContent: "center",
    alignItems: "center",
  },
  ratingButtonText: {
    fontSize: 16,
    fontWeight: "bold",
    color: "white",
  },
  posterImage: {
    width: "100%",
    height: "100%",
    borderRadius: 8,
  },
  modalContainer: {
    flex: 1,
    padding: 16,
    paddingTop: 32,
    alignItems: "center",
  },
  modalTitle: {
    marginBottom: 16,
  },
  movieSelectItem: {
    width: 300,
    maxWidth: 500,
    flexDirection: "row",
    alignItems: "center",
    padding: 12,
    backgroundColor: "rgba(255, 255, 255, 0.05)",
    borderRadius: 8,
    gap: 12,
    borderBottomWidth: 1,
    borderBottomColor: "rgba(255, 255, 255, 0.1)",
    marginVertical: 6,
  },
  closeButton: {
    ...globalStyles.infoCloseButton,
    width: "100%",
    alignSelf: "center",
  },

  // Context menu delete item 
  deleteMenuItem: {
    borderBottomWidth: 0,
    zIndex: 1000,
  },
  deleteMenuText: {
    color: "#FF3B30",
    zIndex: 1000,
  },

  // Info modal  
  infoContainer: {
    flex: 1,
    padding: 16,
    paddingTop: 32,
  },
  infoTitle: {
    marginBottom: 16,
    textAlign: "center",
  },
  infoPosterImage: {
    width: "100%",
    height: "100%",
    borderRadius: 12,
  },
  virtueTitle: {
    marginTop: 16,
    marginBottom: 10,
    fontSize: 17,
    fontWeight: "700",
  },
  virtueGrid: {
    flexDirection: "row",
    gap: 12,
    marginBottom: 8,
  },
  virtueColumn: {
    flex: 1,
    gap: 8,
  },
  virtueRow: {
    gap: 4,
  },
  virtueRowHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  virtueLabel: {
    fontSize: 13,
    fontWeight: "600",
  },
  virtueValue: {
    fontSize: 12,
    opacity: 0.85,
    fontWeight: "700",
  },
  virtueBarTrack: {
    height: 8,
    borderRadius: 999,
    backgroundColor: "rgba(255,255,255,0.14)",
    overflow: "hidden",
  },
  virtueBarFill: {
    height: "100%",
    borderRadius: 999,
  },
  infoRating: {
    fontSize: 16,
    fontWeight: "bold",
    marginTop: 16,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: "rgba(255, 255, 255, 0.1)",
  },
});