import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { ThemedText } from "@/components/themed-text";
import { ThemedView } from "@/components/themed-view";
import { getCatalogMovies, sendChatMessage } from "../../src/db/database";
import { loadUserInfo } from "../../src/storage/userinfo";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
};

export default function ChatScreen() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [watchedMovies, setWatchedMovies] = useState<Array<{
    id: number;
    title: string;
    release_date: string | null;
    rating: number | null;
  }>>([]);
  const flatListRef = useRef<FlatList>(null);

  useEffect(() => {
    (async () => {
      try {
        const [userInfo, movies] = await Promise.all([
          loadUserInfo(),
          getCatalogMovies(100),
        ]);

        const watched = movies
          .filter((m) => userInfo.watchedMovieIds.includes(m.id))
          .map((m) => ({
            id: m.id,
            title: m.title,
            release_date: m.release_date || null,
            rating: userInfo.ratings[m.id] || null,
          }));

        setWatchedMovies(watched);

        const welcomeMessage: ChatMessage = {
          id: "welcome",
          role: "assistant",
          content:
            watched.length > 0
              ? `I've loaded your ${watched.length} watched movies. Based on your preferences, what kind of movie would you like to watch next? I can recommend something similar to what you've enjoyed.`
              : "Welcome! Tell me what kind of movies you like, and I can recommend something great for you.",
          timestamp: Date.now(),
        };
        setMessages([welcomeMessage]);
      } catch (error) {
        console.error("Failed to initialize chat", error);
        const errorMessage: ChatMessage = {
          id: "error",
          role: "assistant",
          content:
            "Sorry, I couldn't load your movie history. But I can still help you find a great movie! What are you in the mood for?",
          timestamp: Date.now(),
        };
        setMessages([errorMessage]);
      } finally {
        setIsInitializing(false);
      }
    })();
  }, []);

  const handleSendMessage = async () => {
    if (!inputText.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: "user",
      content: inputText,
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputText("");
    setIsLoading(true);

    try {
      // Build a rich prompt with context and instructions
      let fullMessage = "You are a friendly and knowledgeable movie recommendation assistant. Your role is to help users discover movies they'll love based on their tastes and previous viewing history. Be conversational, enthusiastic about cinema, and provide thoughtful recommendations with brief explanations.\n\n";

      if (watchedMovies.length > 0) {
        fullMessage += "Here are the movies the user has watched and their ratings:\n";
        watchedMovies.forEach((movie) => {
          const ratingStr = movie.rating ? `${movie.rating}/10` : "not rated";
          const year = movie.release_date?.split("-")[0] || "unknown year";
          fullMessage += `- ${movie.title} (${year}) - ${ratingStr}\n`;
        });
        fullMessage += "\nUse this context to understand their preferences and recommend similar or complementary films.\n\n";
      } else {
        fullMessage +=
          "The user hasn't watched any movies in their history yet. Help them discover great films based on what they tell you they like.\n\n";
      }

      fullMessage += `User's question: ${inputText}`;

      const response = await sendChatMessage({
        message: fullMessage,
        model: "qwen3.6:35b",
        temperature: 0.7,
      });

      const assistantMessage: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: "assistant",
        content: response.reply,
        timestamp: Date.now(),
      };

      setMessages((prev) => [...prev, assistantMessage]);

      flatListRef.current?.scrollToEnd({ animated: true });
    } catch (error) {
      console.error("Chat error:", error);
      const errorMessage: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: "assistant",
        content:
          "Sorry, I encountered an error. Please try again. Maybe the server is down.",
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  if (isInitializing) {
    return (
      <ThemedView style={styles.container}>
        <View style={styles.centerContent}>
          <ActivityIndicator size="large" />
          <ThemedText style={styles.loadingText}>
            Loading your movie history...
          </ThemedText>
        </View>
      </ThemedView>
    );
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      style={styles.container}
    >
      <FlatList
        ref={flatListRef}
        data={messages}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.messagesContainer}
        renderItem={({ item }) => (
          <View
            style={[
              styles.messageBubble,
              item.role === "user" ? styles.userBubble : styles.assistantBubble,
            ]}
          >
            <ThemedText
              style={[
                styles.messageText,
                item.role === "user" && styles.userMessageText,
              ]}
            >
              {item.content}
            </ThemedText>
          </View>
        )}
      />

      <View style={styles.inputContainer}>
        <TextInput
          style={styles.input}
          placeholder="Ask for a movie recommendation..."
          placeholderTextColor="rgba(255,255,255,0.5)"
          value={inputText}
          onChangeText={setInputText}
          multiline
          maxLength={500}
          editable={!isLoading}
        />
        <TouchableOpacity
          style={[styles.sendButton, isLoading && styles.sendButtonDisabled]}
          onPress={handleSendMessage}
          disabled={isLoading || !inputText.trim()}
        >
          {isLoading ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <ThemedText style={styles.sendButtonText}>Send</ThemedText>
          )}
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  centerContent: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    gap: 16,
  },
  loadingText: {
    marginTop: 12,
  },
  messagesContainer: {
    padding: 16,
    paddingBottom: 20,
  },
  messageBubble: {
    marginVertical: 8,
    padding: 12,
    borderRadius: 12,
    maxWidth: "85%",
  },
  userBubble: {
    alignSelf: "flex-end",
    backgroundColor: "#007AFF",
  },
  assistantBubble: {
    alignSelf: "flex-start",
    backgroundColor: "rgba(255,255,255,0.1)",
  },
  messageText: {
    fontSize: 15,
    lineHeight: 20,
  },
  userMessageText: {
    color: "#fff",
  },
  inputContainer: {
    flexDirection: "row",
    padding: 12,
    gap: 8,
    alignItems: "flex-end",
  },
  input: {
    flex: 1,
    backgroundColor: "rgba(255,255,255,0.1)",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: "#fff",
    fontSize: 15,
    maxHeight: 100,
    borderColor: "rgba(255,255,255,0.2)",
    borderWidth: 1,
  },
  sendButton: {
    backgroundColor: "#007AFF",
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
    justifyContent: "center",
    alignItems: "center",
  },
  sendButtonDisabled: {
    opacity: 0.5,
  },
  sendButtonText: {
    color: "#fff",
    fontWeight: "600",
    fontSize: 15,
  },
});
