"use client";

import { useState, useEffect, useCallback } from "react";

const STORAGE_KEY_PREFIX = "flowforge-view-mode-";

/**
 * Custom hook to persist view mode preference to localStorage
 * @param key - Unique key for this view mode (e.g., "tools", "functions", "events")
 * @param defaultMode - Default view mode if none is saved
 * @returns [viewMode, setViewMode] tuple
 */
export function useViewMode<T extends string>(
  key: string,
  defaultMode: T
): [T, (mode: T) => void] {
  const storageKey = `${STORAGE_KEY_PREFIX}${key}`;

  // Initialize with default, then update from localStorage on mount
  const [viewMode, setViewModeState] = useState<T>(defaultMode);
  const [isInitialized, setIsInitialized] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        setViewModeState(stored as T);
      }
    } catch {
      // localStorage not available (SSR or privacy mode)
    }
    setIsInitialized(true);
  }, [storageKey]);

  // Save to localStorage when viewMode changes
  const setViewMode = useCallback(
    (mode: T) => {
      setViewModeState(mode);
      try {
        localStorage.setItem(storageKey, mode);
      } catch {
        // localStorage not available
      }
    },
    [storageKey]
  );

  return [viewMode, setViewMode];
}

/**
 * Hook for persisting any preference to localStorage
 * @param key - Unique key for this preference
 * @param defaultValue - Default value if none is saved
 * @returns [value, setValue] tuple
 */
export function usePreference<T>(
  key: string,
  defaultValue: T
): [T, (value: T) => void] {
  const storageKey = `flowforge-pref-${key}`;

  const [value, setValueState] = useState<T>(defaultValue);

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        setValueState(JSON.parse(stored) as T);
      }
    } catch {
      // localStorage not available or invalid JSON
    }
  }, [storageKey]);

  // Save to localStorage when value changes
  const setValue = useCallback(
    (newValue: T) => {
      setValueState(newValue);
      try {
        localStorage.setItem(storageKey, JSON.stringify(newValue));
      } catch {
        // localStorage not available
      }
    },
    [storageKey]
  );

  return [value, setValue];
}
