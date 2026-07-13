<script lang="ts">
    import { onMount, untrack } from "svelte";
    import type { Message } from "$lib/stores/chat";
    import {
        connectWebSocket,
        refreshSessions,
        loadModels,
        currentMessages,
        currentSessionId,
        currentIsGenerating,
        sessions,
        switchSession,
        createNewSession,
    } from "$lib/stores/chat";
    import Sidebar from "$lib/components/chat/Sidebar.svelte";
    import ChatMessage from "$lib/components/chat/ChatMessage.svelte";
    import ChatInput from "$lib/components/chat/ChatInput.svelte";
    import { MessageSquare, Sun, Moon, Menu } from "lucide-svelte";
    import { get } from "svelte/store";
    import { mode, toggleMode } from "mode-watcher";
    import { Button } from "$lib/components/ui/button";
    import * as Sheet from "$lib/components/ui/sheet";

    let scrollAreaViewport = $state<HTMLElement | null>(null);
    let isAtBottom = true;
    let userScrolledUp = false;
    let previousSessionId: string | null = null;
    let previousMessages: Message[] = [];

    function handleScroll(e: Event) {
        const target = e.target as HTMLElement;
        const threshold = 100; // px
        const atBottom =
            target.scrollHeight - target.scrollTop - target.clientHeight <
            threshold;
        isAtBottom = atBottom;
        if (!atBottom) {
            userScrolledUp = true;
        }
    }

    onMount(async () => {
        connectWebSocket();
        await refreshSessions();
        await loadModels();

        const s = get(sessions);
        if (s.length > 0) {
            await switchSession(s[0].session_id);
        } else {
            await createNewSession();
        }
    });

    // Auto-scroll to bottom when messages change
    $effect(() => {
        const messages = $currentMessages;
        const sessionId = $currentSessionId;
        const isGen = $currentIsGenerating;
        const viewport = scrollAreaViewport;

        if (messages && viewport) {
            untrack(() => {
                const sessionChanged = previousSessionId !== sessionId;
                const messagesChanged = messages !== previousMessages;

                previousSessionId = sessionId;
                previousMessages = messages;

                if (!sessionChanged && !messagesChanged) return;

                // Reset scroll state on session switch so the new chat starts fresh.
                if (sessionChanged) {
                    userScrolledUp = false;
                    isAtBottom = true;
                }

                // The newest message is a user message exactly when the user just
                // sent something — always jump to the bottom in that case,
                // regardless of any prior `userScrolledUp` state.
                const lastMessage = messages[messages.length - 1];
                const justSentUserMessage =
                    messagesChanged &&
                    lastMessage &&
                    lastMessage.role === "user";

                // History was just loaded for this session (empty → non-empty
                // while not generating). Always scroll so the user sees the
                // latest messages.
                const historyJustLoaded =
                    messagesChanged &&
                    previousMessages.length === 0 &&
                    messages.length > 0 &&
                    !isGen;

                const shouldScroll =
                    justSentUserMessage ||
                    sessionChanged ||
                    historyJustLoaded ||
                    (isGen && isAtBottom && !userScrolledUp);

                if (shouldScroll) {
                    // Use "auto" (instant) for all programmatic scrolls so the
                    // smooth-scroll animation doesn't fire intermediate scroll
                    // events that would incorrectly set `userScrolledUp`.
                    setTimeout(() => {
                        viewport.scrollTo({
                            top: viewport.scrollHeight,
                            behavior: "auto",
                        });
                        isAtBottom = true;
                    }, 50);
                }
            });
        }
    });
</script>

<div class="flex h-screen w-full overflow-hidden bg-background">
    <aside class="hidden md:block w-64 shrink-0 h-full">
        <Sidebar />
    </aside>

    <main class="flex-1 flex flex-col h-full relative overflow-hidden">
        <header
            class="h-14 border-b flex items-center justify-between px-4 md:px-6 bg-background/95 backdrop-blur shrink-0 gap-4"
        >
            <div class="flex items-center gap-2 md:gap-0">
                <div class="md:hidden">
                    <Sheet.Root>
                        <Sheet.Trigger>
                            {#snippet child({ props })}
                                <Button variant="ghost" size="icon" {...props}>
                                    <Menu class="h-5 w-5" />
                                    <span class="sr-only">Toggle Sidebar</span>
                                </Button>
                            {/snippet}
                        </Sheet.Trigger>
                        <Sheet.Content side="left" class="p-0 w-72">
                            <Sidebar />
                        </Sheet.Content>
                    </Sheet.Root>
                </div>
                <h1 class="font-semibold text-sm">
                    {#if $currentSessionId}
                        {$sessions.find(
                            (s) => s.session_id === $currentSessionId,
                        )?.title || "New Chat"}
                    {:else}
                        Select a chat
                    {/if}
                </h1>
            </div>

            <Button variant="ghost" size="icon" onclick={toggleMode}>
                {#if mode.current === "dark"}
                    <Moon class="h-4 w-4" />
                {:else}
                    <Sun class="h-4 w-4" />
                {/if}
                <span class="sr-only">Toggle theme</span>
            </Button>
        </header>

        <div
            class="flex-1 overflow-y-auto min-h-0 py-4 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
            bind:this={scrollAreaViewport}
            onscroll={handleScroll}
        >
            <div
                class="max-w-4xl w-full mx-auto px-4 flex flex-col gap-6 min-h-full pb-4"
            >
                {#each $currentMessages as message}
                    <ChatMessage {message} />
                {/each}

                {#if $currentMessages.length === 0}
                    <div
                        class="flex-1 flex flex-col items-center justify-center text-muted-foreground gap-4 opacity-50"
                    >
                        <div class="rounded-full bg-muted p-4">
                            <MessageSquare
                                class="h-8 w-8 text-muted-foreground"
                            />
                        </div>
                        <p class="text-sm font-medium">
                            How can I help you today?
                        </p>
                    </div>
                {/if}
            </div>
        </div>

        <div class="max-w-4xl w-full mx-auto shrink-0 px-4">
            <ChatInput />
        </div>
    </main>
</div>

<style>
    :global(html, body) {
        height: 100%;
        overflow: hidden;
    }
</style>
