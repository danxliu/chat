<script lang="ts">
    import type { Message } from "$lib/stores/chat";
    import Markdown from "./Markdown.svelte";
    import ThinkingProcess from "./ThinkingProcess.svelte";
    import { cn } from "$lib/utils";
    import Attachment from "./Attachment.svelte";
    import DynamicChart from "./DynamicChart.svelte";
    import Continuations from "./Continuations.svelte";

    let {
        message,
        isStreaming = false,
    }: { message: Message; isStreaming?: boolean } = $props();

    const isAssistant = $derived(message.role === "assistant");
    const isUser = $derived(message.role === "user");
    const isSystem = $derived(message.role === "system");
</script>

<div
    class={cn(
        "flex w-full flex-col gap-1",
        isUser ? "items-end" : "items-start",
    )}
>
    {#if message.attachments && message.attachments.length > 0}
        <div class="flex flex-wrap gap-2">
            {#each message.attachments as attachment}
                <Attachment {attachment} />
            {/each}
        </div>
    {/if}

    <div
        class={cn(
            "text-sm transition-all flex flex-col gap-1",
            isUser
                ? "chat-bubble-user max-w-[85%] rounded-lg px-4 py-2 bg-primary text-primary-foreground shadow-sm"
                : "w-full py-1",
            isSystem &&
                "bg-destructive/10 text-destructive border border-destructive/20 max-w-full italic px-4 rounded-lg",
        )}
    >
        {#if message.thought || message.isThinking}
            <ThinkingProcess
                thought={message.thought}
                isThinking={message.isThinking}
            />
        {/if}

        {#if message.blocks && message.blocks.length > 0}
            <div class="flex flex-col gap-2">
                {#each message.blocks as block (block.index)}
                    {#if block.type === "text"}
                        <Markdown
                            content={block.content}
                            {isUser}
                            {isStreaming}
                        />
                    {:else if block.type === "chart"}
                        <DynamicChart
                            type={block.content.chart_type}
                            title={block.content.title}
                            data={block.content.data}
                            labelKey={block.content.label_key}
                            valueKeys={block.content.value_keys}
                        />
                    {:else if block.type === "continuations"}
                        <Continuations
                            continuations={block.content.continuations}
                        />
                    {/if}
                {/each}
            </div>
        {/if}

        {#if message.metrics && isAssistant}
            <div class="text-[10px] text-muted-foreground opacity-70">
                Generated {message.metrics.tokens} tokens in {message.metrics.time_s.toFixed(
                    2,
                )}s ({message.metrics.tokens_per_sec.toFixed(1)} t/s)
            </div>
        {/if}
    </div>
</div>
