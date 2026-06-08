import { useSyncExternalStore } from "react";

const STORAGE_KEY = "behaviorguard-theme";
const DEFAULT_THEME = "dark";

let currentTheme = DEFAULT_THEME;
const listeners = new Set();

function notify() {
  listeners.forEach((listener) => listener());
}

function applyTheme(theme) {
  if (typeof document === "undefined") {
    return;
  }

  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
  document.body.dataset.theme = theme;
}

export function initializeTheme() {
  if (typeof window === "undefined") {
    return DEFAULT_THEME;
  }

  const storedTheme = window.localStorage.getItem(STORAGE_KEY);
  currentTheme = storedTheme === "light" || storedTheme === "dark" ? storedTheme : DEFAULT_THEME;
  applyTheme(currentTheme);
  return currentTheme;
}

export function setTheme(theme) {
  if (theme !== "light" && theme !== "dark") {
    return;
  }

  currentTheme = theme;
  if (typeof window !== "undefined") {
    window.localStorage.setItem(STORAGE_KEY, theme);
  }
  applyTheme(theme);
  notify();
}

export function toggleTheme() {
  setTheme(currentTheme === "dark" ? "light" : "dark");
}

function subscribe(listener) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot() {
  return currentTheme;
}

export function useTheme() {
  const theme = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);

  return {
    theme,
    isDark: theme === "dark",
    setTheme,
    toggleTheme,
  };
}
