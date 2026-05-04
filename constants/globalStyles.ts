import { StyleSheet } from "react-native";

export const globalStyles = StyleSheet.create({
  // Common buttons
  primaryButton: {
    padding: 12,
    backgroundColor: "#007AFF",
    borderRadius: 8,
    alignItems: "center",
  },
  primaryButtonText: {
    color: "white",
    fontWeight: "bold",
  },
  closeButton: {
    padding: 12,
    backgroundColor: "#007AFF",
    borderRadius: 8,
    alignItems: "center",
    marginTop: 16,
    maxWidth: 500,
  },
  closeButtonText: {
    color: "white",
    fontWeight: "bold",
  },

  // Menu button
  menuButton: {
    padding: 8,
    position: "absolute",
  },
  menuIcon: {
    fontSize: 20,
    fontWeight: "bold",
  },

  // Search bar
  searchBar: {
    backgroundColor: "rgba(255, 255, 255, 0.1)",
    borderColor: "#ccc",
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
    fontSize: 16,
    color: "#fff",
  },

  // Overlay / Modal
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
  overlayCloseButton: {
    padding: 12,
    backgroundColor: "rgba(255, 255, 255, 0.2)",
    borderRadius: 8,
    alignItems: "center",
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

  // Menu modal
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

  // FAB (Floating Action Button)
  fab: {
    position: "absolute",
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

  // Poster placeholder
  posterPlaceholder: {
    width: 60,
    height: 90,
    backgroundColor: "gray",
    justifyContent: "center",
    alignItems: "center",
    borderRadius: 4,
    flexShrink: 0,
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

  // Movie list
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
  movieContent: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  movieInfo: {
    flex: 1,
    gap: 4,
  },
  categories: {
    fontSize: 14,
    opacity: 0.8,
  },
  // Used on any modal that presents a scrollable list of selectable items
  modalListContent: {
    paddingBottom: 20,
    alignItems: "center",
  },
});