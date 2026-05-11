import ParallaxScrollView from "@/components/parallax-scroll-view";
import { ThemedText } from "@/components/themed-text";
import { ThemedView } from "@/components/themed-view";
import { Image } from "expo-image";
import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import tinycolor from "tinycolor2";

type Movie = {
  id: number;
  title: string;
  poster: string;
  categories: string[];
};
const movies: Movie[] = [
  {
    id: 1,
    title: "Princess Mononoke",
    poster: "placeholder",
    categories: ["Courage", "wisdom"],
  },
  {
    id: 2,
    title: "Iron Man",
    poster: "placeholder",
    categories: ["Courage", "Wisdom"],
  },
  {
    id: 3,
    title: "Up",
    poster: "placeholder",
    categories: ["Humanity"],
  },
];

export default function HomeScreen() {
  const [toggles, setToggles] = useState({
    Wisdom: { state: false, deactColor: "#457", actColor: "#9af" },
    Humanity: { state: false, deactColor: "#172", actColor: "#2e4" },
    Purpose: { state: false, deactColor: "#662", actColor: "#cc4" },
    Justice: { state: false, deactColor: "#526", actColor: "#a4e" },
    Restraint: { state: false, deactColor: "#445", actColor: "#88a" },
    Courage: { state: false, deactColor: "#751", actColor: "#fa2" },
  });

  const activeCategories = Object.entries(toggles)
    .filter(([_, v]) => v.state)
    .map(([key]) => key);

  const filteredMovies = movies.filter((movie) =>
    movie.categories.some((cat: any) => activeCategories.includes(cat)),
  );

  function toggle(key: keyof typeof toggles) {
    console.log(activeCategories);
    setToggles((prev) => ({
      ...prev,
      [key]: {
        ...prev[key],
        state: !prev[key].state,
      },
    }));
  }
  console.log(activeCategories);
  return (
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
        <ThemedText type="title">EudAImonic</ThemedText>
      </ThemedView>
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

      <View style={{ marginTop: 20 }}>
        {filteredMovies.map((movie) => (
          <View key={movie.id} style={styles.movieItem}>
            <Text>{movie.title}</Text>
          </View>
        ))}
      </View>
    </ParallaxScrollView>
  );
}

const styles = StyleSheet.create({
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
  buttonContainer: {
    flexDirection: "row",
    flexWrap: "wrap",
    padding: 16,
  },
  button: {
    width: "30%",
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
  movieItem: {
    padding: 12,
    marginBottom: 8,
    backgroundColor: "#777",
    borderRadius: 8,
  },
});
