import AsyncStorage from "@react-native-async-storage/async-storage";
import * as SecureStore from "expo-secure-store";

import type { CatalogMovie, ScoredMovie } from "../db/database";

export const USER_INFO_STORAGE_KEY = "eudaimonic.userinfo.v1";
export const WATCH_PROVIDER_STORAGE_KEY = "eudaimonic.watchproviders.v1";

export type UserVirtueProfile = {
  wisdom: number;
  courage: number;
  humanity: number;
  justice: number;
  temperance: number;
  transcendence: number;
};

export type UserInfo = {
  watchedMovieIds: number[];
  watchedMovies: CatalogMovie[];
  ratings: Record<number, number>;
  reviews: Record<number, string>;

  userVirtueProfile?: UserVirtueProfile;
};

const DEFAULT_USER_INFO: UserInfo = {
  watchedMovieIds: [],
  watchedMovies: [],
  ratings: {},
  reviews: {},
};

export function buildUserVirtueProfileFromMovies(
  movies: ScoredMovie[]
): UserVirtueProfile {
  if (!movies.length) {
    return {
      wisdom: 1,
      courage: 1,
      humanity: 1,
      justice: 1,
      temperance: 1,
      transcendence: 1,
    };
  }



  const sum = {
    wisdom: 0,
    courage: 0,
    humanity: 0,
    justice: 0,
    temperance: 0,
    transcendence: 0,
  };

  for (const m of movies) {
    sum.wisdom += m.Wisdom;
    sum.courage += m.Courage;
    sum.humanity += m.Humanity;
    sum.justice += m.Justice;
    sum.temperance += m.Temperance;
    sum.transcendence += m.Transcendence;
  }

  const n = movies.length;

  return {
    wisdom: sum.wisdom / n,
    courage: sum.courage / n,
    humanity: sum.humanity / n,
    justice: sum.justice / n,
    temperance: sum.temperance / n,
    transcendence: sum.transcendence / n,
  };
}

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
      watchedMovies: Array.isArray(parsed.watchedMovies)
        ? parsed.watchedMovies.filter((movie): movie is CatalogMovie =>
            Boolean(movie) && typeof movie === "object" && typeof (movie as CatalogMovie).id === "number"
          )
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

export async function loadSelectedProviderIds(): Promise<number[]> {
  try {
    let raw: string | null = null;
    try {
      raw = await AsyncStorage.getItem(WATCH_PROVIDER_STORAGE_KEY);
    } catch (err: any) {
      const msg = String(err?.message || err);
      if (msg.includes("Native module is null") || msg.includes("cannot access legacy storage")) {
        raw = await SecureStore.getItemAsync(WATCH_PROVIDER_STORAGE_KEY);
      } else {
        throw err;
      }
    }

    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];

    return parsed.filter((id): id is number => typeof id === "number");
  } catch {
    return [];
  }
}

export async function saveSelectedProviderIds(providerIds: number[]): Promise<void> {
  const uniqueIds = Array.from(new Set(providerIds.filter((id) => Number.isInteger(id))));
  const payload = JSON.stringify(uniqueIds);

  try {
    await AsyncStorage.setItem(WATCH_PROVIDER_STORAGE_KEY, payload);
  } catch (err: any) {
    const msg = String(err?.message || err);
    if (msg.includes("Native module is null") || msg.includes("cannot access legacy storage")) {
      await SecureStore.setItemAsync(WATCH_PROVIDER_STORAGE_KEY, payload);
      return;
    }
    throw err;
  }
}
