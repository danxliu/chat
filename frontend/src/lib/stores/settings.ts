import { writable } from "svelte/store";
import { browser } from "$app/environment";

export interface Settings {
  llmModel: string;
  llmBaseUrl: string;
  embedModel: string;
  embedBaseUrl: string;
}

export interface BackendDefaults {
  llm_model: string;
  llm_api_base: string;
  embedding_model: string;
  embed_api_base: string;
}

const DEFAULT_SETTINGS: Settings = {
  llmModel: "",
  llmBaseUrl: "",
  embedModel: "",
  embedBaseUrl: "",
};

const storedSettings = browser ? localStorage.getItem("agent-settings") : null;
const initialSettings: Settings = storedSettings
  ? { ...DEFAULT_SETTINGS, ...JSON.parse(storedSettings) }
  : DEFAULT_SETTINGS;

export const settings = writable<Settings>(initialSettings);
export const backendDefaults = writable<BackendDefaults | null>(null);

export async function fetchBackendDefaults() {
  try {
    const res = await fetch("/api/chats/config");
    if (res.ok) {
      const data = await res.json();
      backendDefaults.set(data);
    }
  } catch (e) {
    console.error("Failed to fetch backend defaults:", e);
  }
}

if (browser) {
  settings.subscribe((value) => {
    localStorage.setItem("agent-settings", JSON.stringify(value));
  });
  fetchBackendDefaults();
}
