<script lang="ts">
    import * as Tooltip from "$lib/components/ui/tooltip";
    import { currentTokenUsage } from "$lib/stores/chat";
    import { Gauge } from "lucide-svelte";

    const SIZE = 28;
    const RADIUS = 10;
    const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

    let usage = $derived($currentTokenUsage);
    let pct = $derived(
        usage.max > 0 ? Math.min(100, Math.round((usage.current / usage.max) * 100)) : 0,
    );
    let dashOffset = $derived(CIRCUMFERENCE * (1 - pct / 100));
    let colorClass = $derived(
        pct >= 75 ? "text-red-500" : pct >= 50 ? "text-amber-500" : "text-emerald-500",
    );

    function formatTokens(n: number): string {
        if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
        if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
        return String(n);
    }
</script>

{#if usage.max > 0}
    <Tooltip.Provider>
        <Tooltip.Root>
            <Tooltip.Trigger>
                <svg
                    width={SIZE}
                    height={SIZE}
                    viewBox="0 0 {SIZE} {SIZE}"
                    class="shrink-0 cursor-pointer"
                    role="meter"
                    aria-valuenow={usage.current}
                    aria-valuemin="0"
                    aria-valuemax={usage.max}
                    aria-label="{pct}% context used"
                >
                    <!-- Background track -->
                    <circle
                        cx={SIZE / 2}
                        cy={SIZE / 2}
                        r={RADIUS}
                        fill="none"
                        stroke="currentColor"
                        stroke-width="4"
                        class="text-muted-foreground/20"
                    />
                    <!-- Progress arc -->
                    <circle
                        cx={SIZE / 2}
                        cy={SIZE / 2}
                        r={RADIUS}
                        fill="none"
                        stroke="currentColor"
                        stroke-width="4"
                        stroke-linecap="round"
                        stroke-dasharray={CIRCUMFERENCE}
                        stroke-dashoffset={dashOffset}
                        transform="rotate(-90 {SIZE / 2} {SIZE / 2})"
                        class={colorClass}
                        style="transition: stroke-dashoffset 0.4s ease"
                    />
                </svg>
            </Tooltip.Trigger>
            <Tooltip.Content side="top" sideOffset={6}>
                <div class="flex items-center gap-1.5 text-xs">
                    <Gauge class="size-3" />
                    <span>
                        {formatTokens(usage.current)} / {formatTokens(usage.max)} tokens
                    </span>
                    <span class="text-muted-foreground">&middot; {pct}%</span>
                </div>
            </Tooltip.Content>
        </Tooltip.Root>
    </Tooltip.Provider>
{/if}
