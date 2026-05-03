import { Text, View } from "react-native";


export function PageShell({ title, children }) {
  return (
    <View style={{ flex: 1, padding: 16 }}>
      <Text style={{ fontSize: 24, marginBottom: 12 }}>{title}</Text>
      {children}
    </View>
  );
}
