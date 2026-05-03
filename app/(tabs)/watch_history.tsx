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

// Movie catalogue - this will eventually come from an API/database
const MovieCatalogue = [
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

// Helper function to extract display information from a catalogue movie object
// This function prepares movie data for display in the watch history list
// When we connect to a real catalogue with more fields, this function will handle the extraction
function extractMovieDisplayInfo(catalogueMovie: any) {
  return {
    id: catalogueMovie.id,
    title: catalogueMovie.title,
    poster: catalogueMovie.poster,
    categories: catalogueMovie.categories,
  };
}

export default function WatchHistoryScreen() {
  const [movies, setMovies] = useState<any[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [ratings, setRatings] = useState<{ [movieId: string]: number }>({});
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [menuPosition, setMenuPosition] = useState({ x: 0, y: 0 });
  const [showRatingOverlay, setShowRatingOverlay] = useState(false);
  const [selectedMovieForRating, setSelectedMovieForRating] =
    useState<any>(null);
  const [showInfoOverlay, setShowInfoOverlay] = useState(false);
  const [selectedMovieForInfo, setSelectedMovieForInfo] = useState<any>(null);
  const [watchHistorySearchQuery, setWatchHistorySearchQuery] = useState("");
  const [addMovieSearchQuery, setAddMovieSearchQuery] = useState("");

  // Search/filter function
  const searchMovies = (movies: any[], query: string): any[] => {
    if (!query.trim()) return movies;
    
    const lowerQuery = query.toLowerCase();
    return movies.filter((movie) => {
      const titleMatch = movie.title.toLowerCase().includes(lowerQuery);
      const categoryMatch = movie.categories.some((cat: string) =>
        cat.toLowerCase().includes(lowerQuery)
      );
      return titleMatch || categoryMatch;
    });
  };

  // Open menu and capture button position
  const openMenu = (movieId: string, event: any) => {
    const { pageX, pageY } = event.nativeEvent;
    setMenuPosition({ x: pageX, y: pageY });
    setOpenMenuId(movieId);
  };
  const getAvailableMovies = () => {
    const historyIds = new Set(movies.map((m) => m.id));
    return MovieCatalogue.filter((movie) => !historyIds.has(movie.id));
  };

  // Add a movie from the catalogue to the watch history
  const addMovieFromCatalogue = (catalogueMovie: any) => {
    const displayInfo = extractMovieDisplayInfo(catalogueMovie);
    setMovies([...movies, displayInfo]);
    setShowAddModal(false);
  };

  // Delete a movie from the watch history
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

  // Rate a movie
  const rateMovie = (score: number) => {
    setRatings({
      ...ratings,
      [selectedMovieForRating.id]: score,
    });
    setShowRatingOverlay(false);
    setSelectedMovieForRating(null);
  };

  // Open information overlay for a specific movie
  const openInfoOverlay = (movie: any) => {
    setSelectedMovieForInfo(movie);
    setShowInfoOverlay(true);
    setOpenMenuId(null);
  };

  // Clear search when modal is closed
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
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.movieItemContainer}
            onPress={() => openInfoOverlay(item)}
            activeOpacity={0.7}
          >
            <ThemedView style={styles.movieItem}>
              {/* Menu button */}
              <TouchableOpacity
                style={styles.menuButton}
                onPress={(e) => openMenu(item.id, e)}
              >
                <ThemedText style={styles.menuIcon}>⋮</ThemedText>
              </TouchableOpacity>

              {/* Movie poster and info */}
              <ThemedView style={styles.movieContent}>
                <ThemedView style={styles.posterPlaceholder}>
                  <ThemedText>Poster</ThemedText>
                </ThemedView>
                <ThemedView style={styles.movieInfo}>
                  <ThemedText
                    type="subtitle"
                    numberOfLines={1}
                    ellipsizeMode="tail"
                  >
                    {item.title}
                  </ThemedText>
                  <ThemedText
                    style={styles.categories}
                    numberOfLines={1}
                    ellipsizeMode="tail"
                  >
                    {item.categories.join(", ")}
                  </ThemedText>
                </ThemedView>
              </ThemedView>

              {/* Rating display */}
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
        contentContainerStyle={styles.listContent}
      />
      <TouchableOpacity
        style={styles.fab}
        onPress={() => setShowAddModal(true)}
      >
        <ThemedText style={styles.fabText}>+</ThemedText>
      </TouchableOpacity>

      {/* Modal for selecting movies to add */}
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
            renderItem={({ item }) => (
              <TouchableOpacity
                style={styles.movieSelectItem}
                onPress={() => addMovieFromCatalogue(item)}
              >
                <ThemedView style={styles.posterPlaceholder}>
                  <ThemedText>Poster</ThemedText>
                </ThemedView>
                <ThemedView style={styles.movieInfo}>
                  <ThemedText type="subtitle">{item.title}</ThemedText>
                  <ThemedText style={styles.categories}>
                    {item.categories.join(", ")}
                  </ThemedText>
                </ThemedView>
              </TouchableOpacity>
            )}
            contentContainerStyle={styles.modalListContent}
          />
          <TouchableOpacity
            style={styles.closeButton}
            onPress={handleCloseAddModal}
          >
            <ThemedText style={styles.closeButtonText}>Close</ThemedText>
          </TouchableOpacity>
        </ThemedView>
      </Modal>

      {/* Rating overlay modal */}
      <Modal
        visible={showRatingOverlay}
        animationType="fade"
        transparent={true}
        onRequestClose={() => setShowRatingOverlay(false)}
      >
        <ThemedView style={styles.overlayContainer}>
          <ThemedView style={styles.overlayContent}>
            <ThemedText type="title" style={styles.overlayTitle}>
              Rate {selectedMovieForRating?.title}
            </ThemedText>
            <ThemedText style={styles.overlayDescription}>
              Select a rating from 1 to 10
            </ThemedText>
            <View style={styles.ratingButtonsContainer}>
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((score) => (
                <TouchableOpacity
                  key={score}
                  style={styles.ratingButton}
                  onPress={() => rateMovie(score)}
                >
                  <ThemedText style={styles.ratingButtonText}>
                    {score}
                  </ThemedText>
                </TouchableOpacity>
              ))}
            </View>
            <TouchableOpacity
              style={styles.overlayCloseButton}
              onPress={() => setShowRatingOverlay(false)}
            >
              <ThemedText style={styles.closeButtonText}>Cancel</ThemedText>
            </TouchableOpacity>
          </ThemedView>
        </ThemedView>
      </Modal>

      {/* Information overlay modal */}
      <Modal
        visible={showInfoOverlay}
        animationType="slide"
        transparent={false}
        onRequestClose={() => setShowInfoOverlay(false)}
      >
        <ThemedView style={styles.infoContainer}>
          <TouchableOpacity
            style={styles.infoCloseButton}
            onPress={() => setShowInfoOverlay(false)}
          >
            <ThemedText style={styles.infoCloseButtonText}>Close</ThemedText>
          </TouchableOpacity>
          <ThemedText type="title" style={styles.infoTitle}>
            {selectedMovieForInfo?.title}
          </ThemedText>
          <ThemedView style={styles.infoPosterPlaceholder}>
            <ThemedText>Poster</ThemedText>
          </ThemedView>
          <ThemedText style={styles.infoPlaceholder}>
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

      {/* Menu modal */}
      <Modal
        visible={openMenuId !== null}
        animationType="fade"
        transparent={true}
        onRequestClose={() => setOpenMenuId(null)}
      >
        <TouchableOpacity
          style={styles.menuModalOverlay}
          activeOpacity={1}
          onPress={() => setOpenMenuId(null)}
        >
          <ThemedView
            style={[
              styles.menuModalContent,
              {
                position: "absolute",
                top: menuPosition.y,
                left: menuPosition.x,
              },
            ]}
          >
            <TouchableOpacity
              style={styles.menuItem}
              onPress={() => {
                const movie = movies.find((m) => m.id === openMenuId);
                if (movie) openRatingOverlay(movie);
              }}
            >
              <ThemedText>Rate Movie</ThemedText>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.menuItem}
              onPress={() => {
                const movie = movies.find((m) => m.id === openMenuId);
                if (movie) openInfoOverlay(movie);
              }}
            >
              <ThemedText>More Information</ThemedText>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.menuItem, styles.deleteMenuItem]}
              onPress={() => {
                if (openMenuId) deleteMovie(openMenuId);
              }}
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
  container: {
    flex: 1,
    padding: 16,
    gap: 16,
  },
  listContent: {
    paddingBottom: 100,
    alignItems: "center",
  },
  movieItemContainer: {
    width: 500,
    aspectRatio: 500 / 140,
    alignSelf: "center",
  },
  movieItem: {
    position: "relative",
    flexDirection: "row",
    alignItems: "center",
    padding: 12,
    backgroundColor: "rgba(255, 255, 255, 0.1)",
    borderRadius: 8,
    gap: 12,
    marginVertical: 6,
    height: "100%",
    zIndex: 1,
  },
  menuButton: {
    padding: 8,
    position: "absolute",
    top: 4,
    right: 4,
    zIndex: 10,
  },
  menuIcon: {
    fontSize: 20,
    fontWeight: "bold",
  },
  movieContent: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
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
  menuModalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0)",
  },
  menuModalContent: {
    backgroundColor: "rgba(0, 0, 0, 0.9)",
    borderRadius: 8,
    overflow: "hidden",
    minWidth: 200,
  },
  menuItem: {
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: "rgba(255, 255, 255, 0.1)",
    zIndex: 1000,
  },
  deleteMenuItem: {
    borderBottomWidth: 0,
    zIndex: 1000,
  },
  deleteMenuText: {
    color: "#FF3B30",
    zIndex: 1000,
  },
  posterPlaceholder: {
    width: 60,
    height: 90,
    backgroundColor: "gray",
    justifyContent: "center",
    alignItems: "center",
    borderRadius: 4,
    flexShrink: 0,
  },
  movieInfo: {
    flex: 1,
    gap: 4,
  },
  categories: {
    fontSize: 14,
    opacity: 0.8,
  },
  fab: {
    position: "absolute",
    bottom: 20,
    right: 20,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: "#007AFF",
    justifyContent: "center",
    alignItems: "center",
    elevation: 5,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 3,
  },
  fabText: {
    fontSize: 24,
    color: "white",
    fontWeight: "bold",
  },
  modalContainer: {
    flex: 1,
    padding: 16,
    paddingTop: 32,
  },
  modalTitle: {
    marginBottom: 16,
  },
  modalListContent: {
    paddingBottom: 20,
    alignItems: "center",
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
    padding: 12,
    backgroundColor: "#007AFF",
    borderRadius: 8,
    alignItems: "center",
    marginTop: 16,
    maxWidth: 500,
    width: "100%",
    alignSelf: "center",
  },
  closeButtonText: {
    color: "white",
    fontWeight: "bold",
  },
  overlayContainer: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.7)",
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
  },
  overlayContent: {
    backgroundColor: "rgba(40, 40, 40, 0.95)",
    borderRadius: 12,
    padding: 24,
    maxWidth: 400,
    width: "100%",
  },
  overlayTitle: {
    marginBottom: 8,
    textAlign: "center",
  },
  overlayDescription: {
    textAlign: "center",
    marginBottom: 20,
    opacity: 0.8,
  },
  searchBar: {
    backgroundColor: "rgba(255, 255, 255, 0.1)",
    borderColor: "#ccc",
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
    fontSize: 16,
    width: "35%",
    alignSelf: "center",
    color: "#fff",
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
  overlayCloseButton: {
    padding: 12,
    backgroundColor: "rgba(255, 255, 255, 0.2)",
    borderRadius: 8,
    alignItems: "center",
  },
  infoContainer: {
    flex: 1,
    padding: 16,
    paddingTop: 32,
  },
  infoCloseButton: {
    padding: 12,
    backgroundColor: "#007AFF",
    borderRadius: 8,
    alignItems: "center",
    marginBottom: 16,
    maxWidth: 100,
  },
  infoCloseButtonText: {
    color: "white",
    fontWeight: "bold",
  },
  infoTitle: {
    marginBottom: 16,
    textAlign: "center",
  },
  infoPosterPlaceholder: {
    width: 120,
    height: 180,
    backgroundColor: "gray",
    justifyContent: "center",
    alignItems: "center",
    borderRadius: 8,
    alignSelf: "center",
    marginBottom: 20,
  },
  infoPlaceholder: {
    fontSize: 14,
    opacity: 0.8,
    marginBottom: 16,
    lineHeight: 20,
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
