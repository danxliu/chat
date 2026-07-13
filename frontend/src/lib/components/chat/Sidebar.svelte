<script lang="ts">
    import {
        sessions,
        currentSessionId,
        switchSession,
        createNewSession,
        deleteSession,
        isConnected,
        disconnectWebSocket,
        connectWebSocket,
        refreshSessions,
        loadModels,
    } from "$lib/stores/chat";
    import { userUUID } from "$lib/stores/user";
    import { Button } from "$lib/components/ui/button";
    import { ScrollArea } from "$lib/components/ui/scroll-area";
    import UserSettings from "$lib/components/UserSettings.svelte";
    import { Plus, MessageSquare, Trash2, Trash, User } from "lucide-svelte";
    import { cn } from "$lib/utils";
    import { get } from "svelte/store";

    let settingsOpen = $state(false);

    async function handleClearAllChats() {
        if (!confirm("Are you sure you want to delete all chats?")) return;
        await fetch("/api/chats", {
            method: "DELETE",
            headers: { "X-User-ID": get(userUUID) },
        });
        await createNewSession();
    }

    async function handleClearMemories() {
        if (!confirm("Are you sure you want to clear all memories?")) return;
        await fetch("/api/chats/memories", {
            method: "DELETE",
            headers: { "X-User-ID": get(userUUID) },
        });
    }

    async function handleUserImported() {
        disconnectWebSocket();
        connectWebSocket();
        await refreshSessions();
        await loadModels();

        const s = get(sessions);
        if (s.length > 0) {
            await switchSession(s[0].session_id);
        } else {
            await createNewSession();
        }
    }
</script>

<div class="flex flex-col h-full border-r bg-muted/30 gap-2">
    <div class="h-14 border-b flex items-center px-6 shrink-0">
        <div class="flex items-center gap-2">
            <div
                class={cn(
                    "w-2 h-2 rounded-full",
                    $isConnected ? "bg-green-500 animate-pulse" : "bg-red-500",
                )}
            ></div>
            <span
                class="text-xs font-semibold uppercase tracking-wider text-muted-foreground"
            >
                {$isConnected ? "Connected" : "Disconnected"}
            </span>
        </div>
    </div>

    <ScrollArea class="flex-1 m-4">
        <div class="flex flex-col gap-2">
            <Button
                onclick={createNewSession}
                class="w-full justify-start gap-2"
                variant="outline"
            >
                <Plus class="h-4 w-4" />
                New Chat
            </Button>
            {#each $sessions as session}
                <div class="group relative">
                    <Button
                        variant={session.session_id === $currentSessionId
                            ? "secondary"
                            : "ghost"}
                        class="w-full justify-start pr-10 truncate"
                        onclick={() => switchSession(session.session_id)}
                    >
                        <MessageSquare class="mr-2 h-4 w-4 shrink-0" />
                        <span class="truncate">{session.title}</span>
                    </Button>
                    <button
                        onclick={(e) => {
                            e.stopPropagation();
                            deleteSession(session.session_id);
                        }}
                        class="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 p-1 hover:text-destructive transition-opacity"
                    >
                        <Trash2 class="h-4 w-4" />
                    </button>
                </div>
            {/each}
        </div>
    </ScrollArea>

    <div class="p-4 mt-auto border-t space-y-2">
        <Button
            variant="ghost"
            size="sm"
            class="w-full justify-start gap-2 text-muted-foreground"
            onclick={() => (settingsOpen = true)}
        >
            <User class="h-4 w-4" />
            User Settings
        </Button>
        <Button
            variant="ghost"
            size="sm"
            class="w-full justify-start gap-2 text-muted-foreground"
            onclick={handleClearMemories}
        >
            <Trash class="h-4 w-4" />
            Clear Memory
        </Button>
        <Button
            variant="ghost"
            size="sm"
            class="w-full justify-start gap-2 text-muted-foreground"
            onclick={handleClearAllChats}
        >
            <Trash class="h-4 w-4" />
            Clear All Chats
        </Button>
    </div>
</div>

<UserSettings bind:open={settingsOpen} onImported={handleUserImported} />
