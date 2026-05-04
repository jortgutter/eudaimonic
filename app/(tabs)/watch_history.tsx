import { useState } from "react";
import {
  FlatList,
  Modal,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { ThemedText } from "@/components/themed-text";
import { ThemedView } from "@/components/themed-view";
import { MovieCatalogue, extractMovieDisplayInfo } from "@/constants/dummycatalogue";
import { globalStyles } from "@/constants/globalStyles";


export default function WatchHistoryScreen() {
  const [movies, setMovies] = useState<any[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [ratings, setRatings] = useState<{ [movieId: string]: number }>({});
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [menuPosition, setMenuPosition] = useState({ x: 0, y: 0 });
  const [showRatingOverlay, setShowRatingOverlay] = useState(false);
  const [selectedMovieForRating, setSelectedMovieForRating] = useState<any>(null);
  const [showInfoOverlay, setShowInfoOverlay] = useState(false);
  const [selectedMovieForInfo, setSelectedMovieForInfo] = useState<any>(null);
  const [watchHistorySearchQuery, setWatchHistorySearchQuery] = useState("");
  const [addMovieSearchQuery, setAddMovieSearchQuery] = useState("");

  // Filter movies based on search query (matches title or categories)
  const searchMovies = (movies: any[], query: string): any[] => {
    if (!query.trim()) return movies;

    const lowerQuery = query.toLowerCase();                               // Case-insensitive search
    return movies.filter((movie) => {
      const titleMatch = movie.title.toLowerCase().includes(lowerQuery);  // Match against title
      const categoryMatch = movie.categories.some((cat: string) =>
        cat.toLowerCase().includes(lowerQuery)                            // Match against any category
      );
      return titleMatch || categoryMatch;                                 // Include movie if it either matches in title or category
    });
  };

  // Open context menu for a specific movie at the tap position
  const openMenu = (movieId: string, event: any) => {
    const { pageX, pageY } = event.nativeEvent;
    setMenuPosition({ x: pageX, y: pageY });
    setOpenMenuId(movieId);
  };

  // Get movies that are not yet in the watch history (for adding new ones)
  const getAvailableMovies = () => {
    const historyIds = new Set(movies.map((m) => m.id));
    return MovieCatalogue.filter((movie) => !historyIds.has(movie.id));
  };

  // Add movie to history
  const addMovieFromCatalogue = (catalogueMovie: any) => {
    const displayInfo = extractMovieDisplayInfo(catalogueMovie);
    setMovies([...movies, displayInfo]);
    setShowAddModal(false);
  };

  // Delete movie from history
  const deleteMovie = (movieId: string) => {
    setMovies(movies.filter((m) => m.id !== movieId));
    setOpenMenuId(null);
  };

  // Open rating overlay for a specific movie
  const openRatingOverlay = (movie: any) => {
    setSelectedMovieForRating(movie);
    setShowRatingOverlay(true);
    setOpenMenuId(null);
  };

  // Handle rating submission
  const rateMovie = (score: number) => {
    setRatings({ ...ratings, [selectedMovieForRating.id]: score });
    setShowRatingOverlay(false);
    setSelectedMovieForRating(null);
  };

  // Open info overlay for a specific movie
  const openInfoOverlay = (movie: any) => {
    setSelectedMovieForInfo(movie);
    setShowInfoOverlay(true);
    setOpenMenuId(null);
  };

  // Handle closing the add-movie modal
  const handleCloseAddModal = () => {
    setShowAddModal(false);
    setAddMovieSearchQuery("");
  };

  return (
    <ThemedView style={styles.container}>
      <ThemedText type="title">Watch History</ThemedText>
      <ThemedText type="subtitle">
        You can view your watched movies here.
      </ThemedText>

      <TextInput
        placeholder="Search movies..."
        value={watchHistorySearchQuery}
        style={styles.searchBar}
        onChangeText={(text) => setWatchHistorySearchQuery(text)}
      />

      <FlatList
        data={searchMovies(movies, watchHistorySearchQuery)}
        keyExtractor={(item) => item.id}
        contentContainerStyle={globalStyles.listContent}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={globalStyles.movieItemContainer}
            onPress={() => openInfoOverlay(item)}
            activeOpacity={0.7}
          >
            <ThemedView style={globalStyles.movieItem}>
              <TouchableOpacity
                style={styles.menuButton}
                onPress={(e) => openMenu(item.id, e)}
              >
                <ThemedText style={globalStyles.menuIcon}>⋮</ThemedText>
              </TouchableOpacity>

              <ThemedView style={globalStyles.movieContent}>
                <ThemedView style={globalStyles.posterPlaceholder}>
                  <ThemedText>Poster</ThemedText>
                </ThemedView>
                <ThemedView style={globalStyles.movieInfo}>
                  <ThemedText type="subtitle" numberOfLines={1} ellipsizeMode="tail">
                    {item.title}
                  </ThemedText>
                  <ThemedText style={globalStyles.categories} numberOfLines={1} ellipsizeMode="tail">
                    {item.categories.join(", ")}
                  </ThemedText>
                </ThemedView>
              </ThemedView>

              <TouchableOpacity
                style={styles.ratingSection}
                onPress={() => openRatingOverlay(item)}
              >
                <ThemedText style={styles.ratingLabel}>Rating</ThemedText>
                <ThemedText style={styles.ratingValue}>
                  {ratings[item.id] ? `${ratings[item.id]}/10` : "Not rated"}
                </ThemedText>
              </TouchableOpacity>
            </ThemedView>
          </TouchableOpacity>
        )}
      />

      <TouchableOpacity
        style={styles.fab}
        onPress={() => setShowAddModal(true)}
      >
        <ThemedText style={globalStyles.fabText}>+</ThemedText>
      </TouchableOpacity>

      {/* Add movie modal */}
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
            data={searchMovies(getAvailableMovies(), addMovieSearchQuery)}
            keyExtractor={(item) => item.id}
            contentContainerStyle={globalStyles.modalListContent}
            renderItem={({ item }) => (
              <TouchableOpacity
                style={styles.movieSelectItem}
                onPress={() => addMovieFromCatalogue(item)}
              >
                <ThemedView style={globalStyles.posterPlaceholder}>
                  <ThemedText>Poster</ThemedText>
                </ThemedView>
                <ThemedView style={globalStyles.movieInfo}>
                  <ThemedText type="subtitle">{item.title}</ThemedText>
                  <ThemedText style={globalStyles.categories}>
                    {item.categories.join(", ")}
                  </ThemedText>
                </ThemedView>
              </TouchableOpacity>
            )}
          />
          <TouchableOpacity
            style={styles.closeButton}
            onPress={handleCloseAddModal}
          >
            <ThemedText style={globalStyles.infoCloseButtonText}>Close</ThemedText>
          </TouchableOpacity>
        </ThemedView>
      </Modal>

      {/* Rating overlay */}
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
            <ThemedText style={globalStyles.overlayDescription}>
              Select a rating from 1 to 10
            </ThemedText>
            <View style={styles.ratingButtonsContainer}>
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((score) => (
                <TouchableOpacity
                  key={score}
                  style={styles.ratingButton}
                  onPress={() => rateMovie(score)}
                >
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

      {/* Info overlay */}
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
            <ThemedText>Poster</ThemedText>
          </ThemedView>
          <ThemedText style={globalStyles.infoPlaceholder}>
            Movie information will be displayed here. This page will eventually
            show genres, cast, description, and all other IMDb-like information.
          </ThemedText>
          {ratings[selectedMovieForInfo?.id] && (
            <ThemedText style={styles.infoRating}>
              Your Rating: {ratings[selectedMovieForInfo?.id]}/10
            </ThemedText>
          )}
        </ThemedView>
      </Modal>

      {/* Context menu */}
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
                const movie = movies.find((m) => m.id === openMenuId);
                if (movie) openRatingOverlay(movie);
              }}
            >
              <ThemedText>Rate Movie</ThemedText>
            </TouchableOpacity>
            <TouchableOpacity
              style={globalStyles.menuItem}
              onPress={() => {
                const movie = movies.find((m) => m.id === openMenuId);
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

  // Add-movie modal 
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
  infoRating: {
    fontSize: 16,
    fontWeight: "bold",
    marginTop: 16,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: "rgba(255, 255, 255, 0.1)",
  },
});