// Seeded bug: `loadSettings` hands back the SAME defaults object every time,
// so two callers that each think they have their own settings are holding
// one object, and tuning one tunes both.
export type Settings = { retries: number };

const DEFAULTS: Settings = { retries: 3 };

export function loadSettings(): Settings {
  return DEFAULTS;              // BUG: the shared object, not a copy
}

export function tune(settings: Settings): Settings {
  settings.retries = 9;
  return settings;
}

export function retriesOf(settings: Settings): number {
  return settings.retries;
}
