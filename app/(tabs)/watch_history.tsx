import { Image } from "expo-image";
import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Dimensions,
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
  TmdbMovieSummary,
  importTmdbMovieToCatalog,
  getMovieVirtueScores,
  searchTmdbMovies,
  VirtueScores
} from "../../src/db/database";
import {
  clearWatchHistory,
  loadUserInfo,
  saveUserInfo
} from "../../src/storage/userinfo";
type RatingsMap = Record<number, number>;
type ReviewsMap = Record<number, string>;

const EMPTY_VIRTUE_SCORES: VirtueScores = {
  wisdom: 0,
  courage: 0,
  humanity: 0,
  justice: 0,
  temperance: 0,
  transcendence: 0,
};

const SCREEN_WIDTH = Dimensions.get("window").width;

export default function WatchHistoryScreen() {
  const [watchedMovieIds, setWatchedMovieIds] = useState<number[]>([]);
  const [watchedMovies, setWatchedMovies] = useState<CatalogMovie[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [ratings, setRatings] = useState<RatingsMap>({});
  const [reviews, setReviews] = useState<ReviewsMap>({});
 
  const [showRatingOverlay, setShowRatingOverlay] = useState(false);
  const [selectedMovieForRating, setSelectedMovieForRating] = useState<CatalogMovie | null>(null);
  const [showReviewOverlay, setShowReviewOverlay] = useState(false);
  const [selectedMovieForReview, setSelectedMovieForReview] = useState<CatalogMovie | null>(null);
  const [reviewDraft, setReviewDraft] = useState("");

  const [showInfoOverlay, setShowInfoOverlay] = useState(false);
  const [selectedMovieForInfo, setSelectedMovieForInfo] = useState<CatalogMovie | null>(null);
  const [selectedMovieVirtues, setSelectedMovieVirtues] = useState<VirtueScores>(EMPTY_VIRTUE_SCORES);
  const [isVirtueLoading, setIsVirtueLoading] = useState(false);
  const [watchHistorySearchQuery, setWatchHistorySearchQuery] = useState("");
  const [addMovieSearchQuery, setAddMovieSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isImporting, setIsImporting] = useState(false);

  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const timeout = setTimeout(async () => {
      const q = addMovieSearchQuery.trim();

      // cancel previous request
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setIsSearching(true);

      try {
        if (!q) {
          setSearchResults([]);
          return;
        }

        const results = await searchTmdbMovies(q, 1);

        // ignore aborted responses
        if (controller.signal.aborted) return;

        setSearchResults(results);
      } catch (err) {
        if (controller.signal.aborted) return;

        console.error("Search failed", err);

        // fallback instead of empty UI
        setSearchResults([]);
      } finally {
        if (!controller.signal.aborted) {
          setIsSearching(false);
        }
      }
    }, 300);

    return () => clearTimeout(timeout);
  }, [addMovieSearchQuery]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const rawUserInfo = await loadUserInfo();
        if (!mounted) return;
        const userInfo = rawUserInfo ?? { watchedMovieIds: [], watchedMovies: [], ratings: {}, reviews: {} };
        setWatchedMovieIds(userInfo.watchedMovieIds ?? []);
        setWatchedMovies(userInfo.watchedMovies ?? []);
        setRatings(userInfo.ratings ?? {});
        setReviews(userInfo.reviews ?? {});
      } catch (err) {
        console.error("Failed loading watch history", err);
        if (!mounted) return;
        setLoadError("Could not load watch history.");
      } finally {
        if (mounted) setIsLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const [searchResults, setSearchResults] = useState<TmdbMovieSummary[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const resetWatchHistory = async () => {
  try {
    await clearWatchHistory();

    setWatchedMovieIds([]);
    setWatchedMovies([]);
    setRatings({});
    setReviews({});

    setLoadError(null);
  } catch (err) {
    console.error("Failed to clear watch history", err);
    setLoadError("Failed to reset watch history.");
  }
};

  const openAddModal = () => {
    setShowAddModal(true);
    setSearchResults([]);
    setAddMovieSearchQuery("");
  };

  async function persistUserInfo(nextIds: number[], nextRatings: RatingsMap, nextMovies: CatalogMovie[] = watchedMovies) {
    try {
      await saveUserInfo({ watchedMovieIds: nextIds, watchedMovies: nextMovies, ratings: nextRatings, reviews });
    } catch (err) {
      console.error("Failed to persist user info", err);
      setLoadError("Failed to save watch history.");
    }
  }

  // function searchMovies(movies: CatalogMovie[], query: string) {
  //   if (!query.trim()) return movies;
  //   const lowerQuery = query.toLowerCase();
  //   return movies.filter((movie) => movie.title.toLowerCase().includes(lowerQuery) || (movie.genres ?? []).some((genre) => genre.toLowerCase().includes(lowerQuery)));
  // }

  const addMovieFromTmdb = async (movie: TmdbMovieSummary) => {
    if (isImporting) return;

    setIsImporting(true);
    try {
      const imported = await importTmdbMovieToCatalog(movie.id);
      const importedMovie = imported.movie;
      const nextIds = Array.from(new Set([...watchedMovieIds, importedMovie.id]));
      const nextMovies = [importedMovie, ...watchedMovies.filter((item) => item.id !== importedMovie.id)];

      setWatchedMovieIds(nextIds);
      setWatchedMovies(nextMovies);
      await saveUserInfo({ watchedMovieIds: nextIds, watchedMovies: nextMovies, ratings, reviews });
      setShowAddModal(false);
      setAddMovieSearchQuery("");
    } catch (err) {
      console.error("Failed to import TMDb movie", err);
      setLoadError("Failed to import movie from TMDb.");
    } finally {
      setIsImporting(false);
    }
  };

  const deleteMovie = async (movieId: number) => {
    const next = watchedMovieIds.filter((id) => id !== movieId);
    const nextRatings = { ...ratings };
    delete nextRatings[movieId];
    const nextReviews = { ...reviews };
    delete nextReviews[movieId];
    const nextMovies = watchedMovies.filter((movie) => movie.id !== movieId);
    setWatchedMovieIds(next);
    setWatchedMovies(nextMovies);
    setRatings(nextRatings);
    setReviews(nextReviews);
    await saveUserInfo({ watchedMovieIds: next, watchedMovies: nextMovies, ratings: nextRatings, reviews: nextReviews });
  };

  const handleDeleteFromInfo = async () => {
    if (!selectedMovieForInfo) return;

    await deleteMovie(selectedMovieForInfo.id);

    setShowInfoOverlay(false);
    setSelectedMovieForInfo(null);
  };

  const openRatingOverlay = (movie: CatalogMovie) => {
    setSelectedMovieForRating(movie);
    setShowRatingOverlay(true);
  };

  const rateMovie = async (score: number) => {
    if (!selectedMovieForRating) return;

    const nextRatings = { ...ratings, [selectedMovieForRating.id]: score };
    setRatings(nextRatings);
    await persistUserInfo(watchedMovieIds, nextRatings, watchedMovies);
    setShowRatingOverlay(false);
    setSelectedMovieForRating(null);
  };

  const openReviewOverlay = (movie: CatalogMovie) => {
    setSelectedMovieForReview(movie);
    setReviewDraft(reviews[movie.id] ?? "");
    setShowReviewOverlay(true);
  };

  const saveReview = async () => {
    if (!selectedMovieForReview) return;

    const nextReviews = {
      ...reviews,
      [selectedMovieForReview.id]: reviewDraft.trim(),
    };

    if (!reviewDraft.trim()) {
      delete nextReviews[selectedMovieForReview.id];
    }

    setReviews(nextReviews);
    await saveUserInfo({ watchedMovieIds, watchedMovies, ratings, reviews: nextReviews });
    setShowReviewOverlay(false);
    setSelectedMovieForReview(null);
    setReviewDraft("");
  };

  const openInfoOverlay = async (movie: CatalogMovie) => {
    setSelectedMovieForInfo(movie);
    setShowInfoOverlay(true);
    setIsVirtueLoading(true);
    try {
      const scores = await getMovieVirtueScores(movie.id);
      setSelectedMovieVirtues(scores ?? EMPTY_VIRTUE_SCORES);
    } catch (err) {
      console.error("Failed to load virtues", err);
      setSelectedMovieVirtues(EMPTY_VIRTUE_SCORES);
    } finally {
      setIsVirtueLoading(false);
    }
  };

  const filteredWatchedMovies = useMemo(() => {
  const q = watchHistorySearchQuery.trim().toLowerCase();

  if (!q) return watchedMovies;

    return watchedMovies.filter((movie) => {
      return (
        movie.title.toLowerCase().includes(q) ||
        (movie.genres ?? []).some((g) => g.toLowerCase().includes(q))
      );
    });
  }, [watchedMovies, watchHistorySearchQuery]);

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
      <ThemedText type="subtitle">Your watched movies.</ThemedText>
      {loadError ? <ThemedText style={{ color: "#FF3B30" }}>{loadError}</ThemedText> : null}
      <TouchableOpacity
        onPress={resetWatchHistory}
        style={{
          marginTop: 8,
          paddingVertical: 8,
          paddingHorizontal: 12,
          borderRadius: 8,
          backgroundColor: "rgba(255,0,0,0.15)",
          alignSelf: "flex-start",
        }}
      >
  <ThemedText style={{ color: "#FF3B30", fontWeight: "700" }}>
    Reset watch history
  </ThemedText>
</TouchableOpacity>
      <TextInput
        placeholder="Search watch history..."
        value={watchHistorySearchQuery}
        onChangeText={setWatchHistorySearchQuery}
        style={[styles.searchBar, { width: Math.min(520, SCREEN_WIDTH - 32) }]}
      />

      <FlatList
        style={{ flex: 1, width: "100%" }}
        contentContainerStyle={styles.listContent}
        data={filteredWatchedMovies}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.itemContainer}
            onPress={() => openInfoOverlay(item)}
            activeOpacity={0.8}
          >
            <View style={styles.itemInner}>
              <View style={globalStyles.posterPlaceholder}>
                {item.image_url ? (
                  <Image source={{ uri: item.image_url }} style={styles.posterImage} />
                ) : (
                  <ThemedText>Poster</ThemedText>
                )}
              </View>

              <View style={styles.infoCol}>
                <ThemedText type="subtitle" numberOfLines={2} ellipsizeMode="tail">
                  {item.title}
                </ThemedText>
                <ThemedText style={globalStyles.categories} numberOfLines={1} ellipsizeMode="tail">
                  {(item.genres ?? []).join(", ") || "No genres"}
                </ThemedText>
              </View>

              <TouchableOpacity style={styles.rateButton} onPress={() => openRatingOverlay(item)}>
                <ThemedText style={styles.rateText}>{ratings[item.id] ? `${ratings[item.id]}/10` : "Rate"}</ThemedText>
              </TouchableOpacity>
              <TouchableOpacity style={styles.reviewButton} onPress={() => openReviewOverlay(item)}>
                <ThemedText style={styles.reviewText}>{reviews[item.id] ? "Edit review" : "Review"}</ThemedText>
              </TouchableOpacity>
            </View>
            {reviews[item.id] ? (
              <ThemedText style={styles.reviewPreview} numberOfLines={2} ellipsizeMode="tail">
                {reviews[item.id]}
              </ThemedText>
            ) : null}
          </TouchableOpacity>
        )}
        ItemSeparatorComponent={() => <View style={{ height: 8 }} />}
        ListEmptyComponent={() => (
          <View style={styles.emptyContainer}>
            <ThemedText>No watched movies yet.</ThemedText>
            <ThemedText>Tap + to add from the catalogue.</ThemedText>
          </View>
        )}
        keyboardShouldPersistTaps="handled"
        initialNumToRender={10}
        showsVerticalScrollIndicator={false}
      />

      <TouchableOpacity style={styles.fab} onPress={openAddModal}>
        <ThemedText style={globalStyles.fabText}>+</ThemedText>
      </TouchableOpacity>

      {/* Add modal (TMDb search + import) */}
      <Modal visible={showAddModal} animationType="slide">
        <ThemedView style={styles.modalRoot}>
          <ThemedText type="title">Search TMDb</ThemedText>
          <TextInput
            placeholder="Search TMDb..."
            value={addMovieSearchQuery}
            onChangeText={(text) => {
              setAddMovieSearchQuery(text);
            }}
            style={styles.searchBar}
          />

          {isSearching ? (
            <View style={{ paddingVertical: 16 }}>
              <ActivityIndicator />
            </View>
          ) : null}

          <FlatList
            data={searchResults}
            keyExtractor={(m) => String(m.id)}
            renderItem={({ item }) => (
              <TouchableOpacity
                style={styles.modalItem}
                onPress={() => addMovieFromTmdb(item)}
                disabled={isImporting}
              >
                <View style={globalStyles.posterPlaceholder}>
                  {item.poster_url ? <Image source={{ uri: item.poster_url }} style={styles.posterImage} /> : <ThemedText>Poster</ThemedText>}
                </View>
                <View style={styles.infoCol}>
                  <ThemedText type="subtitle">{item.title}</ThemedText>
                  <ThemedText style={globalStyles.categories}>
                    {item.release_date?.split("-")[0] || `TMDb #${item.id}`}
                  </ThemedText>
                </View>
              </TouchableOpacity>
            )}
            ListEmptyComponent={() => (
              <View style={styles.emptyContainer}>
                <ThemedText>Search TMDb to add any movie.</ThemedText>
              </View>
            )}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          />

          <TouchableOpacity style={globalStyles.infoCloseButton} onPress={() => setShowAddModal(false)}>
            <ThemedText style={globalStyles.infoCloseButtonText}>Close</ThemedText>
          </TouchableOpacity>
        </ThemedView>
      </Modal>

      {/* Rating overlay */}
      <Modal visible={showRatingOverlay} transparent animationType="fade">
        <ThemedView style={globalStyles.overlayContainer}>
          <View style={globalStyles.overlayContent}>
            <ThemedText type="title">Rate {selectedMovieForRating?.title}</ThemedText>
            <View style={styles.ratingRow}>
              {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
                <TouchableOpacity key={n} style={styles.ratingButton} onPress={() => rateMovie(n)}>
                  <ThemedText style={styles.ratingButtonText}>{n}</ThemedText>
                </TouchableOpacity>
              ))}
            </View>
            <TouchableOpacity style={{ marginTop: 12 }} onPress={() => setShowRatingOverlay(false)}>
              <ThemedText>Cancel</ThemedText>
            </TouchableOpacity>
          </View>
        </ThemedView>
      </Modal>

      <Modal visible={showReviewOverlay} transparent animationType="fade">
        <ThemedView style={globalStyles.overlayContainer}>
          <View style={styles.reviewOverlayContent}>
            <ThemedText type="title">Write a review</ThemedText>
            <ThemedText style={styles.reviewOverlaySubtitle}>
              {selectedMovieForReview?.title}
            </ThemedText>
            <TextInput
              value={reviewDraft}
              onChangeText={setReviewDraft}
              placeholder="Write what you thought about this movie..."
              placeholderTextColor="rgba(255,255,255,0.5)"
              multiline
              textAlignVertical="top"
              style={styles.reviewInput}
              maxLength={1000}
            />
            <View style={styles.reviewOverlayActions}>
              <TouchableOpacity style={styles.reviewSaveButton} onPress={saveReview}>
                <ThemedText style={styles.reviewSaveText}>Save review</ThemedText>
              </TouchableOpacity>
              <TouchableOpacity style={styles.reviewCancelButton} onPress={() => setShowReviewOverlay(false)}>
                <ThemedText>Cancel</ThemedText>
              </TouchableOpacity>
            </View>
          </View>
        </ThemedView>
      </Modal>

      {/* Info overlay */}
      <Modal visible={showInfoOverlay} animationType="slide">
        <ThemedView style={styles.infoRoot}>
          <TouchableOpacity style={globalStyles.infoCloseButton} onPress={() => setShowInfoOverlay(false)}>
            <ThemedText style={globalStyles.infoCloseButtonText}>Close</ThemedText>
          </TouchableOpacity>

          <ThemedText type="title">{selectedMovieForInfo?.title}</ThemedText>
            {selectedMovieForInfo && (
              <TouchableOpacity
                style={{
                  marginTop: 12,
                  paddingVertical: 10,
                  paddingHorizontal: 12,
                  backgroundColor: "rgba(255, 59, 48, 0.15)",
                  borderRadius: 8,
                  alignSelf: "flex-start",
                }}
                onPress={handleDeleteFromInfo}
              >
                <ThemedText style={{ color: "#FF3B30", fontWeight: "700" }}>
                  Remove from history
                </ThemedText>
              </TouchableOpacity>
            )}
          <View style={globalStyles.infoPosterPlaceholder}>
            {selectedMovieForInfo?.image_url ? (
              <Image source={{ uri: selectedMovieForInfo.image_url }} style={styles.infoPoster} />
            ) : (
              <ThemedText>Poster</ThemedText>
            )}
          </View>

          <ThemedText style={globalStyles.infoPlaceholder}>{selectedMovieForInfo?.summary || "No summary."}</ThemedText>

          <ThemedText type="subtitle">Virtue Scores</ThemedText>
          {isVirtueLoading ? (
            <ActivityIndicator />
          ) : (
            <View style={styles.virtuesGrid}>
              {Object.entries(selectedMovieVirtues).map(([k, v]) => (
                <View key={k} style={styles.virtueRow}>
                  <ThemedText style={{ fontWeight: "600" }}>{k}</ThemedText>
                  <ThemedText>{Math.round((v ?? 0) * 100) / 100}</ThemedText>
                </View>
              ))}
            </View>
          )}

          {selectedMovieForInfo && ratings[selectedMovieForInfo.id] && (
            <ThemedText>Your rating: {ratings[selectedMovieForInfo.id]}/10</ThemedText>
          )}

          {selectedMovieForInfo && reviews[selectedMovieForInfo.id] ? (
            <>
              <ThemedText type="subtitle" style={styles.infoReviewTitle}>
                Your review
              </ThemedText>
              <ThemedText style={styles.infoReviewText}>{reviews[selectedMovieForInfo.id]}</ThemedText>
            </>
          ) : null}
        </ThemedView>
      </Modal>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  // Screen-level layout 
  container: {
    flex: 1,
    padding: 16,
    alignItems: "center",
    gap: 12,
  },

  // Search bar (global base + local width constraint)   
  searchBar: {
    ...globalStyles.searchBar,
    width: "100%",
    maxWidth: 520,
  },
  listContent: {
    paddingBottom: 120,
    width: "100%",
  },
  itemContainer: {
    width: "100%",
    alignSelf: "center",
  },
  itemInner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    padding: 12,
    backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 10,
  },
  infoCol: {
    flex: 1,
  },
  posterImage: {
    width: "100%",
    height: "100%",
    borderRadius: 6,
  },
  rateButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: "rgba(255,255,255,0.04)",
  },
  rateText: {
    fontWeight: "700",
  },
  reviewButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: "rgba(0,122,255,0.12)",
  },
  reviewText: {
    fontWeight: "700",
    color: "#9BC9FF",
  },
  reviewPreview: {
    marginTop: 8,
    fontSize: 13,
    lineHeight: 18,
    opacity: 0.8,
  },
  fab: {
    ...globalStyles.fab,
    width: 56,
    height: 56,
    borderRadius: 28,
    right: 20,
    bottom: 20,
  },
  modalRoot: {
    flex: 1,
    padding: 16,
    paddingTop: 32,
  },
  modalItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: "rgba(255,255,255,0.03)",
  },
  emptyContainer: {
    padding: 24,
    alignItems: "center",
  },
  ratingRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    marginTop: 12,
  },
  ratingButton: {
    width: 36,
    height: 36,
    borderRadius: 6,
    backgroundColor: "#007AFF",
    alignItems: "center",
    justifyContent: "center",
  },
  ratingButtonText: {
    color: "white",
    fontWeight: "700",
  },
  reviewOverlayContent: {
    ...globalStyles.overlayContent,
    width: "100%",
    maxWidth: 500,
    gap: 12,
  },
  reviewOverlaySubtitle: {
    opacity: 0.8,
  },
  reviewInput: {
    minHeight: 160,
    backgroundColor: "rgba(255,255,255,0.05)",
    borderRadius: 12,
    padding: 12,
    color: "#fff",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
  },
  reviewOverlayActions: {
    flexDirection: "row",
    gap: 12,
    justifyContent: "flex-end",
  },
  reviewSaveButton: {
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: "#007AFF",
  },
  reviewSaveText: {
    color: "white",
    fontWeight: "700",
  },
  reviewCancelButton: {
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: "rgba(255,255,255,0.08)",
  },
  infoRoot: {
    flex: 1,
    padding: 16,
    paddingTop: 32,
  },
  infoPoster: {
    width: "100%",
    height: "100%",
    borderRadius: 8,
  },
  virtuesGrid: {
    marginTop: 12,
    gap: 8,
  },
  virtueRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 6,
  },
  infoReviewTitle: {
    marginTop: 16,
  },
  infoReviewText: {
    marginTop: 4,
    lineHeight: 20,
  },
});
