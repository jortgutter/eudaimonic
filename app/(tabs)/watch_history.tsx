import Ionicons from "@expo/vector-icons/Ionicons";
import { Image } from "expo-image";
import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Dimensions,
  FlatList,
  Modal,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { ThemedText } from "@/components/themed-text";
import { ThemedView } from "@/components/themed-view";
import { globalStyles } from "@/constants/globalStyles";
import {
  CatalogMovie,
  getMovieVirtueScores,
  importTmdbMovieToCatalog,
  resolveTmdbGenres,
  searchTmdbMovies,
  TmdbMovieSummary,
  VirtueScores
} from "../../src/db/database";
import {
  clearWatchHistory,
  loadUserInfo,
  saveUserInfo,
  UserVirtueProfile
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
const VIRTUE_COLORS: Record<string, string> = {
  wisdom:        "#9af",
  humanity:      "#2e4",
  transcendence: "#cc4",
  justice:       "#a4e",
  temperance:    "#88a",
  courage:       "#fa2",
};

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
    <View style={{ marginBottom: 4 }}>
      <View style={{ flexDirection: "row", alignItems: "center" }}>
        <Text style={{ color: "#afa6a6", width: 110, marginRight: 8 }}>
          {label}:
        </Text>
        <View
          style={{
            flex: 1,
            height: 8,
            backgroundColor: "#544d4d",
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
        <Text style={{ color: "#afa6a6", width: 36, marginLeft: 8 }}>
          {clamped.toFixed(2)}
        </Text>
      </View>
    </View>
  );
};

async function buildMovieVirtueMap(
  movies: CatalogMovie[]
): Promise<Record<number, VirtueScores>> {
  const entries = await Promise.all(
    movies.map(async (m) => {
      const v = await getMovieVirtueScores(m.id);
      return [m.id, v ?? EMPTY_VIRTUE_SCORES] as const;
    })
  );

  return Object.fromEntries(entries);
}

function computeUserVirtueProfile(
  movies: CatalogMovie[],
  ratings: RatingsMap,
  movieVirtueMap: Record<number, VirtueScores>
): UserVirtueProfile {
  const profile: UserVirtueProfile = {
    wisdom: 0,
    courage: 0,
    humanity: 0,
    justice: 0,
    temperance: 0,
    transcendence: 0,
  };

  let totalWeight = 0;

  for (const movie of movies) {
    const virtues = movieVirtueMap[movie.id];
    if (!virtues) continue;

    const rating = ratings[movie.id] ?? 5.5;
    const weight = rating - 5.5; // center around neutral
    console.log("movie_id:", movie.title);
    console.log("rating:", rating);
    console.log("weight:", weight);

    if (weight === 0) continue;

    totalWeight += Math.abs(weight);

    profile.wisdom += virtues.wisdom * weight;
    profile.courage += virtues.courage * weight;
    profile.humanity += virtues.humanity * weight;
    profile.justice += virtues.justice * weight;
    profile.temperance += virtues.temperance * weight;
    profile.transcendence += virtues.transcendence * weight;
  }

  if (totalWeight > 0) {
    for (const k of Object.keys(profile) as (keyof UserVirtueProfile)[]) {
      profile[k] /= totalWeight;
    }
  }
  console.log("wis:", profile.wisdom);
  console.log("cou:", profile.courage);
  console.log("hum:", profile.humanity);
  console.log("justice:", profile.justice);
  console.log("tem:", profile.temperance);
  console.log("tra:", profile.transcendence);

  return profile;
}

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
  const [importingMovieTitle, setImportingMovieTitle] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  const recomputeAndPersistProfile = async (
    movies: CatalogMovie[],
    ratings: RatingsMap,
    watchedIds: number[]

  ) => {
    const movieVirtueMap = await buildMovieVirtueMap(movies);

    const profile = computeUserVirtueProfile(movies, ratings, movieVirtueMap);

    const userInfo = await loadUserInfo();

    await saveUserInfo({
      ...(userInfo ?? {}),
      watchedMovieIds: watchedIds,
      watchedMovies: movies,
      ratings,
      reviews,
      userVirtueProfile: profile,
    });

    return profile;
  };

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

async function persistUserInfo(
  nextIds: number[],
  nextRatings: RatingsMap,
  nextMovies: CatalogMovie[] = watchedMovies,
  nextReviews: ReviewsMap = reviews,
  profile: UserVirtueProfile
) {
  try {
    await saveUserInfo({
      watchedMovieIds: nextIds,
      watchedMovies: nextMovies,
      ratings: nextRatings,
      reviews: nextReviews,
      userVirtueProfile: profile,
    });
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
    setImportingMovieTitle(movie.title);
    try {
      const optimisticMovie: CatalogMovie = {
        id: movie.id,
        title: movie.title,
        summary: movie.overview ?? null,
        image_url: movie.poster_url ?? null,
        vote_average: movie.vote_average ?? null,
        release_date: movie.release_date ?? null,
        adult: false,
        genres: resolveTmdbGenres(movie.genre_ids),
      };

      const nextIds = Array.from(new Set([...watchedMovieIds, optimisticMovie.id]));
      const nextMovies = [optimisticMovie, ...watchedMovies.filter((item) => item.id !== optimisticMovie.id)];

      setWatchedMovieIds(nextIds);
      setWatchedMovies(nextMovies);
      //await saveUserInfo({ watchedMovieIds: nextIds, watchedMovies: nextMovies, ratings, reviews });

      await recomputeAndPersistProfile(nextMovies, ratings, nextIds);
      
      void importTmdbMovieToCatalog(movie.id).catch((err) => {
        console.error("Failed to import TMDb movie", err);
      });
      setShowAddModal(false);
      setAddMovieSearchQuery("");
    } catch (err) {
      console.error("Failed to import TMDb movie", err);
      setLoadError("Failed to import movie from TMDb.");
    } finally {
      setIsImporting(false);
      setImportingMovieTitle(null);
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
    //await saveUserInfo({ watchedMovieIds: next, watchedMovies: nextMovies, ratings: nextRatings, reviews: nextReviews });

    await recomputeAndPersistProfile(nextMovies, nextRatings, next);
    

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
    //await persistUserInfo(watchedMovieIds, nextRatings, watchedMovies);

    await recomputeAndPersistProfile(watchedMovies, nextRatings, watchedMovieIds);

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
    //await saveUserInfo({ watchedMovieIds, watchedMovies, ratings, reviews: nextReviews });

    await recomputeAndPersistProfile(watchedMovies, ratings, watchedMovieIds);

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
              <TouchableOpacity style={styles.deleteButton} onPress={() => deleteMovie(item.id)}>
                <Ionicons name="trash-outline" size={20} color="#FF3B30" />
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
          <ThemedText type="title">Search movie to add</ThemedText>
          <TextInput
            placeholder="Search TMDb..."
            value={addMovieSearchQuery}
            onChangeText={(text) => {
              setAddMovieSearchQuery(text);
            }}
            style={styles.searchBar}
            editable={!isImporting}
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

          <TouchableOpacity style={globalStyles.infoCloseButton} onPress={() => setShowAddModal(false)} disabled={isImporting}>
            <ThemedText style={globalStyles.infoCloseButtonText}>Close</ThemedText>
          </TouchableOpacity>

          {isImporting ? (
            <View style={styles.importOverlay}>
              <ActivityIndicator size="large" />
              <ThemedText style={styles.importOverlayTitle}>Adding movie...</ThemedText>
              <ThemedText style={styles.importOverlaySubtitle} numberOfLines={1}>
                {importingMovieTitle ?? "Please wait"}
              </ThemedText>
            </View>
          ) : null}
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

      {/* Info overlay from home screen */}
      <Modal visible={showInfoOverlay} transparent animationType="fade">
        <View style={styles.infoModalBackdrop}>
          <View style={styles.infoModalContent}>
            {selectedMovieForInfo && (
              <>
                <Image
                  source={{ uri: selectedMovieForInfo.image_url ?? undefined }}
                  style={styles.infoModalPoster}
                />

                <Text style={styles.infoModalTitle}>{selectedMovieForInfo.title}</Text>

                {selectedMovieForInfo.release_date ? (
                  <Text style={styles.infoModalYear}>{selectedMovieForInfo.release_date}</Text>
                ) : null}

                {selectedMovieForInfo.vote_average != null ? (
                  <Text style={styles.infoModalRating}>
                    IMDb: {selectedMovieForInfo.vote_average}/10
                  </Text>
                ) : null}

                {ratings[selectedMovieForInfo.id] ? (
                  <Text style={styles.infoModalUserRating}>
                    Your rating: {ratings[selectedMovieForInfo.id]}/10
                  </Text>
                ) : null}

                <ScrollView style={styles.infoModalScroll} showsVerticalScrollIndicator={false}>
                  <Text style={styles.infoModalDescription}>
                    {selectedMovieForInfo.summary || "No summary available."}
                  </Text>

                  <Text style={styles.infoModalSectionTitle}>Virtue Scores</Text>

                  {isVirtueLoading ? (
                    <ActivityIndicator style={{ marginVertical: 12 }} />
                  ) : (
                    <View style={styles.infoModalTraits}>
                      {Object.entries(selectedMovieVirtues).map(([key, value]) => (
                        <TraitBar
                          key={key}
                          label={key.charAt(0).toUpperCase() + key.slice(1)}
                          value={value}
                          color={VIRTUE_COLORS[key] ?? "#888"}
                        />
                      ))}
                    </View>
                  )}

                  {reviews[selectedMovieForInfo.id] ? (
                    <>
                      <Text style={styles.infoModalSectionTitle}>Your review</Text>
                      <Text style={styles.infoModalReview}>
                        {reviews[selectedMovieForInfo.id]}
                      </Text>
                    </>
                  ) : null}

                  <TouchableOpacity
                    style={styles.infoModalDeleteButton}
                    onPress={handleDeleteFromInfo}
                  >
                    <Text style={styles.infoModalDeleteText}>Remove from history</Text>
                  </TouchableOpacity>
                </ScrollView>

                <TouchableOpacity
                  style={styles.infoModalCloseButton}
                  onPress={() => {
                    setShowInfoOverlay(false);
                    setSelectedMovieForInfo(null);
                  }}
                >
                  <Text style={styles.infoModalCloseText}>Close</Text>
                </TouchableOpacity>
              </>
            )}
          </View>
        </View>
      </Modal>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    alignItems: "center",
    gap: 12,
  },
  searchBar: {
    ...globalStyles.searchBar,
    width: "100%",
    maxWidth: 520,
  },
  resetButton: {
    marginTop: 8,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    backgroundColor: "rgba(255,0,0,0.15)",
    alignSelf: "flex-start",
  },
  resetButtonText: {
    color: "#FF3B30",
    fontWeight: "700",
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
  deleteButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: "rgba(255,255,255,0.04)",
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
  importOverlay: {
    ...StyleSheet.absoluteFillObject,
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    paddingHorizontal: 24,
  },
  importOverlayTitle: {
    fontSize: 18,
    fontWeight: "700",
  },
  importOverlaySubtitle: {
    opacity: 0.85,
    textAlign: "center",
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

  // Info overlay styles
  infoModalBackdrop: {
    flex: 1,
    backgroundColor: "#0B0C1D",
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
  },
  infoModalContent: {
    width: "100%",
    maxWidth: 400,
    backgroundColor: "#222",
    borderRadius: 16,
    padding: 20,
    alignItems: "center",
    maxHeight: "90%",
  },
  infoModalPoster: {
    width: 180,
    height: 270,
    borderRadius: 12,
    marginBottom: 16,
  },
  infoModalTitle: {
    fontSize: 22,
    fontWeight: "bold",
    color: "white",
    textAlign: "center",
  },
  infoModalYear: {
    color: "#bbb",
    marginTop: 4,
  },
  infoModalRating: {
    color: "#f5c518",
    marginTop: 4,
    fontSize: 16,
  },
  infoModalUserRating: {
    color: "#9BC9FF",
    marginTop: 4,
    fontSize: 14,
  },
  infoModalScroll: {
    width: "100%",
    maxHeight: 320,
    marginTop: 12,
  },
  infoModalDescription: {
    color: "#b0d0df",
    textAlign: "justify",
    lineHeight: 20,
    marginBottom: 16,
  },
  infoModalSectionTitle: {
    color: "white",
    fontWeight: "700",
    fontSize: 16,
    marginBottom: 8,
    marginTop: 4,
  },
  infoModalTraits: {
    width: "100%",
    marginBottom: 16,
  },
  infoModalReview: {
    color: "#b0d0df",
    lineHeight: 20,
    marginBottom: 16,
  },
  infoModalDeleteButton: {
    paddingVertical: 10,
    paddingHorizontal: 12,
    backgroundColor: "rgba(255, 59, 48, 0.15)",
    borderRadius: 8,
    alignSelf: "flex-start",
    marginBottom: 8,
  },
  infoModalDeleteText: {
    color: "#FF3B30",
    fontWeight: "700",
  },
  infoModalCloseButton: {
    marginTop: 16,
    backgroundColor: "#444",
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 10,
  },
  infoModalCloseText: {
    color: "white",
    fontWeight: "600",
  },
});