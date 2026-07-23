<script lang="ts">
    import { Copy, Check } from "lucide-svelte";

    let { text }: { text: string } = $props();

    let copied = $state(false);
    let timeout: ReturnType<typeof setTimeout> | null = null;

    async function handleCopy() {
        try {
            await navigator.clipboard.writeText(text);
            copied = true;
            if (timeout) clearTimeout(timeout);
            timeout = setTimeout(() => {
                copied = false;
            }, 2000);
        } catch {
            // Clipboard API unavailable — silently ignore
        }
    }
</script>

<button
    type="button"
    onclick={handleCopy}
    class="inline-flex items-center gap-1 hover:opacity-100 transition-opacity cursor-pointer"
    aria-label={copied ? "Copied" : "Copy response"}
>
    {#if copied}
        <Check class="h-3 w-3" />
    {:else}
        <Copy class="h-3 w-3" />
    {/if}
</button>
