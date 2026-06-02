<script lang="ts">
    import {
        Toaster as Sonner,
        type ToasterProps as SonnerProps,
    } from "svelte-sonner";
    import { mode } from "mode-watcher";
    import Loader2Icon from "@lucide/svelte/icons/loader-2";
    import CircleCheckIcon from "@lucide/svelte/icons/circle-check";
    import InfoIcon from "@lucide/svelte/icons/info";
    import { CircleAlertIcon, CircleXIcon } from "lucide-svelte";

    let { ...restProps }: SonnerProps = $props();
</script>

<Sonner
    theme={mode.current}
    class="toaster group"
    style="--normal-bg: var(--color-popover); --normal-text: var(--color-popover-foreground); --normal-border: var(--color-border);"
    {...restProps}
>
    {#snippet loadingIcon()}
        <Loader2Icon class="size-4 animate-spin" />
    {/snippet}
    {#snippet successIcon()}
        <CircleCheckIcon class="size-4" />
    {/snippet}
    {#snippet errorIcon()}
        <CircleXIcon class="size-4 text-destructive" />
    {/snippet}
    {#snippet infoIcon()}
        <InfoIcon class="size-4" />
    {/snippet}
    {#snippet warningIcon()}
        <CircleAlertIcon class="size-4 text-yellow-500" />
    {/snippet}
</Sonner>
