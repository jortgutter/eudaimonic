import { StyleSheet } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';

export default function SettingsScreen() {
  return (
    <ThemedView style={styles.container}>
      <ThemedText type="title">Settings</ThemedText>
      <ThemedView style={styles.stepContainer}>
        <ThemedText type="subtitle">Preferences</ThemedText>
        <ThemedText>Configure your app settings here.</ThemedText>
      </ThemedView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    gap: 16,
  },
  stepContainer: {
    gap: 8,
    marginBottom: 8,
  },
});
