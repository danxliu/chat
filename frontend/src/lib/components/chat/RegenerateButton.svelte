<script lang="ts">
    import { RefreshCw } from "lucide-svelte";
    import { regenerateResponse } from "$lib/stores/chat";

    function handleRegenerate() {
        regenerateResponse();
    }
</script>

<button
    type="button"
    onclick={handleRegenerate}
    class="inline-flex items-center hover:opacity-100 transition-opacity cursor-pointer"
    aria-label="Regenerate response"
>
    <RefreshCw class="h-3 w-3" />
</button>
