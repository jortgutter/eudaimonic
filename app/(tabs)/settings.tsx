import { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { ThemedText } from "@/components/themed-text";
import { ThemedView } from "@/components/themed-view";
import { getWatchProviders, WatchProvider } from "../../src/db/database";
import { loadSelectedProviderIds, saveSelectedProviderIds } from "../../src/storage/userinfo";

const COUNTRY_CODE = "NL";

export default function SettingsScreen() {
  const [providers, setProviders] = useState<WatchProvider[]>([]);
  const [selectedProviderIds, setSelectedProviderIds] = useState<number[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isCancelled = false;

    const run = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const [fetchedProviders, savedProviderIds] = await Promise.all([
          getWatchProviders(COUNTRY_CODE),
          loadSelectedProviderIds(),
        ]);

        if (isCancelled) return;

        setProviders(fetchedProviders);
        setSelectedProviderIds(savedProviderIds);
      } catch (err) {
        if (isCancelled) return;
        console.error("Failed to load watch providers", err);
        setError("Could not load watch providers. Please try again.");
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    };

    run();

    return () => {
      isCancelled = true;
    };
  }, []);

  const selectedSet = useMemo(() => new Set(selectedProviderIds), [selectedProviderIds]);

  const onToggleProvider = (providerId: number) => {
    setSelectedProviderIds((prev) => {
      const exists = prev.includes(providerId);
      const next = exists ? prev.filter((id) => id !== providerId) : [...prev, providerId];
      saveSelectedProviderIds(next).catch((err) => {
        console.error("Failed to save watch providers", err);
        setError("Could not save your changes. Please try again.");
      });
      return next;
    });
  };

  const onSelectAll = () => {
    const next = providers.map((provider) => provider.provider_id);
    setSelectedProviderIds(next);
    saveSelectedProviderIds(next).catch((err) => {
      console.error("Failed to save watch providers", err);
      setError("Could not save your changes. Please try again.");
    });
  };

  const onClearAll = () => {
    setSelectedProviderIds([]);
    saveSelectedProviderIds([]).catch((err) => {
      console.error("Failed to save watch providers", err);
      setError("Could not save your changes. Please try again.");
    });
  };

return (
  <View style={styles.container}>
    <ScrollView contentContainerStyle={styles.scrollContent}>
      {/* Changed from ThemedView to View to drop the weird background box */}
        <View style={styles.titleContainer}>
          <ThemedText type="title">Watch Providers</ThemedText>
        </View>    
      <ThemedText style={styles.subtitle}>
        Choose one or more providers. Recommendations on the Home screen are restricted to selected providers in the Netherlands.
      </ThemedText>

      <View style={styles.actionsRow}>
        <Pressable style={styles.actionButton} onPress={onSelectAll}>
          <Text style={styles.actionText}>Select all</Text>
        </Pressable>
        <Pressable style={styles.actionButton} onPress={onClearAll}>
          <Text style={styles.actionText}>Clear</Text>
        </Pressable>
      </View>

      <Text style={styles.selectionSummary}>
        {selectedProviderIds.length} selected
      </Text>

      {error ? <Text style={styles.errorText}>{error}</Text> : null}

      {isLoading ? (
        <View style={styles.loaderWrap}>
          <ActivityIndicator size="small" />
          <Text style={styles.loaderText}>Loading providers...</Text>
        </View>
      ) : (
        <View style={styles.providerListContent}>
          {providers.map((provider) => {
            const isActive = selectedSet.has(provider.provider_id);
            return (
              <Pressable
                key={provider.provider_id}
                onPress={() => onToggleProvider(provider.provider_id)}
                style={({ pressed }) => [
                  styles.providerRow,
                  isActive && styles.providerRowActive,
                  pressed && styles.providerRowPressed,
                ]}
              >
                <Text style={[styles.providerName, isActive && styles.providerNameActive]}>
                  {provider.provider_name}
                </Text>
                <Text style={[styles.providerStatus, isActive && styles.providerStatusActive]}>
                  {isActive ? "Selected" : "Tap to select"}
                </Text>
              </Pressable>
            );
          })}
        </View>
      )}
    </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#121212", 
  },
  scrollContent: {
    paddingHorizontal: 20,
    paddingTop: 16, 
    paddingBottom: 32,
  },
  titleContainer: {
    flexDirection: "row",
    gap: 8,
    marginBottom: 12,
    backgroundColor: "transparent", 
  },
  subtitle: {
    opacity: 0.8,
    marginBottom: 20,
    color: "#E2E2E2", 
  },
  actionsRow: {
    flexDirection: "row",
    gap: 10,
    marginBottom: 16,
  },
  actionButton: {
    backgroundColor: "rgba(255,255,255,0.12)", 
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  actionText: {
    fontSize: 12,
    fontWeight: "700",
    color: "#ECE9E3", 
  },
  selectionSummary: {
    fontWeight: "700",
    marginBottom: 12,
    color: "#FFFFFF", 
  },
  errorText: {
    color: "#EF5350",
    marginBottom: 8,
  },
  loaderWrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingVertical: 16,
  },
  loaderText: {
    color: "#B0BEC5", 
  },
  providerListContent: {
    gap: 8,
    paddingBottom: 24,
  },
  providerRow: {
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
    borderRadius: 12,
    padding: 12,
    backgroundColor: "rgba(255,255,255,0.06)",
    gap: 4,
  },
  providerRowActive: {
    borderColor: "#8E8578",
    backgroundColor: "rgba(142,133,120,0.3)",
  },
  providerRowPressed: {
    opacity: 0.7,
  },
  providerName: {
    fontWeight: "700",
    color: "#ECE9E3", 
  },
  providerNameActive: {
    color: "#FFFFFF", 
  },
  providerStatus: {
    fontSize: 12,
    color: "#B0B0B0", 
  },
  providerStatusActive: {
    color: "#DFDCD7", 
  },
});