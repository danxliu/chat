<script lang="ts">
    import {
        sessions,
        currentSessionId,
        switchSession,
        createNewSession,
        deleteSession,
        isConnected,
    } from "$lib/stores/chat";
    import { Button } from "$lib/components/ui/button";
    import { Separator } from "$lib/components/ui/separator";
    import { ScrollArea } from "$lib/components/ui/scroll-area";
    import {
        Plus,
        MessageSquare,
        Trash2,
        Database,
        Trash,
    } from "lucide-svelte";
    import { cn } from "$lib/utils";

    async function handleDeletePersonalHistory() {
        if (
            !confirm(
                "Are you sure you want to delete your personal history? This will erase all learned memories.",
            )
        )
            return;
        const res = await fetch("/api/chats/memory", { method: "DELETE" });
        if (res.ok) alert("Personal history deleted.");
    }

    async function handleClearAllChats() {
        if (!confirm("Are you sure you want to clear ALL chat history?"))
            return;
        await fetch("/api/chats", { method: "DELETE" });
        await createNewSession();
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
        <div class="flex flex-col gap-4">
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
            onclick={handleClearAllChats}
        >
            <Trash class="h-4 w-4" />
            Clear All Chats
        </Button>
        <Button
            variant="ghost"
            size="sm"
            class="w-full justify-start gap-2 text-muted-foreground"
            onclick={handleDeletePersonalHistory}
        >
            <Database class="h-4 w-4" />
            Clear Memory
        </Button>
    </div>
</div>
