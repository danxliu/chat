<script lang="ts">
    import { Button } from "$lib/components/ui/button";
    import { sendMessage, isGenerating } from "$lib/stores/chat";

    let { continuations }: { continuations: string[] } = $props();

    function handleContinuation(text: string) {
        if ($isGenerating) return;
        sendMessage(text);
    }
</script>

<div class="flex flex-wrap gap-2">
    {#each continuations as text}
        <Button 
            variant="outline" 
            size="sm" 
            class="text-xs text-left h-auto py-2 px-3 border-primary/20 hover:border-primary/50 hover:bg-primary/5 rounded-full transition-colors"
            onclick={() => handleContinuation(text)}
            disabled={$isGenerating}
        >
            <span class="break-words line-clamp-2">{text}</span>
        </Button>
    {/each}
</div>
