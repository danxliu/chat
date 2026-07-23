<script lang="ts">
    import * as Collapsible from "$lib/components/ui/collapsible";
    import { Button } from "$lib/components/ui/button";
    import { ChevronDown, Brain } from "lucide-svelte";
    import Markdown from "./Markdown.svelte";

    let { thought = "", isThinking = false } = $props();
    let isOpen = $state(false);

    const statusText = $derived(
        isThinking ? "Thinking..." : "View Thought Process",
    );
</script>

<div>
    <Collapsible.Root bind:open={isOpen} class="space-y-1">
        <Collapsible.Trigger
            class="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
            <Brain class="h-3 w-3" />
            <span>{statusText}</span>
            <ChevronDown
                class="h-3 w-3 transition-transform duration-200 {isOpen
                    ? 'rotate-180'
                    : ''}"
            />
        </Collapsible.Trigger>
        <Collapsible.Content class="space-y-1">
            <div class="rounded-md border bg-muted/30 p-3 text-sm">
                <Markdown content={thought} />
            </div>
        </Collapsible.Content>
    </Collapsible.Root>
</div>
