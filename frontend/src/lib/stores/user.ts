import { writable, derived } from "svelte/store";

const STORAGE_KEY = "chat_user_uuid";

const uuid = writable<string | null>(null);

export const userUUID = derived(uuid, ($uuid) => {
	if ($uuid === null) {
		throw new Error("User UUID not initialized — await isReady before using.");
	}
	return $uuid;
});

export const isReady = derived(uuid, ($uuid) => $uuid !== null);

export function initUserUUID(): string {
	const stored = localStorage.getItem(STORAGE_KEY);
	if (stored) {
		uuid.set(stored);
		return stored;
	}
	const newUUID = crypto.randomUUID();
	localStorage.setItem(STORAGE_KEY, newUUID);
	uuid.set(newUUID);
	return newUUID;
}

export function importUUID(newUUID: string): boolean {
	const trimmed = newUUID.trim();
	if (!trimmed) return false;

	// Basic UUID validation (allows any hex-based UUID format)
	const uuidRegex =
		/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
	if (!uuidRegex.test(trimmed)) return false;

	localStorage.setItem(STORAGE_KEY, trimmed);
	uuid.set(trimmed);
	return true;
}

// Initialize immediately (localStorage is synchronous)
initUserUUID();
