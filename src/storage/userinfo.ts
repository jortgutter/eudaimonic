import AsyncStorage from "@react-native-async-storage/async-storage";
import * as SecureStore from "expo-secure-store";

export const USER_INFO_STORAGE_KEY = "eudaimonic.userinfo.v1";

export type UserInfo = {
  watchedMovieIds: number[];
  ratings: Record<string, number>;
  reviews: Record<string, string>;
};

const DEFAULT_USER_INFO: UserInfo = {
  watchedMovieIds: [],
  ratings: {},
  reviews: {},
};

export async function loadUserInfo(): Promise<UserInfo> {
  try {
    let raw: string | null = null;
    try {
      raw = await AsyncStorage.getItem(USER_INFO_STORAGE_KEY);
    } catch (err: any) {
      const msg = String(err?.message || err);
      if (msg.includes("Native module is null") || msg.includes("cannot access legacy storage")) {
        // Fallback to SecureStore when AsyncStorage native module isn't available (Expo Go)
        raw = await SecureStore.getItemAsync(USER_INFO_STORAGE_KEY);
      } else {
        throw err;
      }
    }
    if (!raw) return DEFAULT_USER_INFO;

    const parsed = JSON.parse(raw) as Partial<UserInfo>;

    return {
      watchedMovieIds: Array.isArray(parsed.watchedMovieIds)
        ? parsed.watchedMovieIds.filter((id): id is number => typeof id === "number")
        : [],
      ratings:
        parsed.ratings && typeof parsed.ratings === "object"
          ? Object.fromEntries(
              Object.entries(parsed.ratings).filter(
                ([key, value]) => typeof key === "string" && typeof value === "number"
              )
            )
          : {},
        reviews:
          parsed.reviews && typeof parsed.reviews === "object"
            ? Object.fromEntries(
                Object.entries(parsed.reviews).filter(
                  ([key, value]) => typeof key === "string" && typeof value === "string"
                )
              )
            : {},
    };
  } catch {
    return DEFAULT_USER_INFO;
  }
}

export async function saveUserInfo(data: UserInfo): Promise<void> {
  const payload = JSON.stringify(data);
  try {
    await AsyncStorage.setItem(USER_INFO_STORAGE_KEY, payload);
  } catch (err: any) {
    const msg = String(err?.message || err);
    if (msg.includes("Native module is null") || msg.includes("cannot access legacy storage")) {
      await SecureStore.setItemAsync(USER_INFO_STORAGE_KEY, payload);
      return;
    }
    throw err;
  }
}

export async function clearWatchHistory(): Promise<void> {
  try {
    await AsyncStorage.removeItem(USER_INFO_STORAGE_KEY);
  } catch (err: any) {
    const msg = String(err?.message || err);

    if (
      msg.includes("Native module is null") ||
      msg.includes("cannot access legacy storage")
    ) {
      await SecureStore.deleteItemAsync(USER_INFO_STORAGE_KEY);
      return;
    }

    throw err;
  }
}
