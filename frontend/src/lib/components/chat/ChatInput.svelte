<script lang="ts">
    import {
        sendMessage,
        currentIsGenerating,
        cancelGeneration,
        activeModel,
        enableReasoning,
        models,
        selectedModel,
        loadModels,
    } from "$lib/stores/chat";
    import { Button } from "$lib/components/ui/button";
    import { Textarea } from "$lib/components/ui/textarea";
    import { Switch } from "$lib/components/ui/switch";
    import { Label } from "$lib/components/ui/label";
    import * as Select from "$lib/components/ui/select";
    import {
        Send,
        Square,
        Paperclip,
        BrainCircuit,
        Cpu,
        X,
        Upload,
    } from "lucide-svelte";
    import type { Attachment as AttachmentType } from "$lib/stores/chat";
    import Attachment from "./Attachment.svelte";
    import { onMount } from "svelte";

    let input = $state("");
    let pendingAttachments = $state<AttachmentType[]>([]);
    let isDragging = $state(false);
    let dragCounter = 0;
    let fileInput: HTMLInputElement;

    onMount(() => {
        loadModels();
    });

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    }

    function handlePaste(e: ClipboardEvent) {
        const items = e.clipboardData?.items;
        let hasFiles = false;
        if (items) {
            for (const item of Array.from(items)) {
                if (item.kind === "file") {
                    const file = item.getAsFile();
                    if (file) {
                        uploadFile(file);
                        hasFiles = true;
                    }
                }
            }
        }
        if (hasFiles) {
            e.preventDefault();
        }
    }

    function handleDragEnter(e: DragEvent) {
        e.preventDefault();
        dragCounter++;
        isDragging = true;
    }

    function handleDragOver(e: DragEvent) {
        e.preventDefault();
    }

    function handleDragLeave(e: DragEvent) {
        e.preventDefault();
        dragCounter--;
        if (dragCounter === 0) {
            isDragging = false;
        }
    }

    async function handleDrop(e: DragEvent) {
        e.preventDefault();
        dragCounter = 0;
        isDragging = false;
        if (e.dataTransfer?.files) {
            for (const file of Array.from(e.dataTransfer.files)) {
                await uploadFile(file);
            }
        }
    }

    async function handleSend() {
        if ($currentIsGenerating) {
            cancelGeneration();
            return;
        }

        if (input.trim() || pendingAttachments.length > 0) {
            sendMessage(input, [...pendingAttachments]);
            input = "";
            pendingAttachments = [];
        }
    }

    async function onFileChange(e: Event) {
        const target = e.target as HTMLInputElement;
        if (target.files) {
            for (const file of Array.from(target.files)) {
                await uploadFile(file);
            }
        }
        target.value = "";
    }

    async function uploadFile(file: File) {
        const formData = new FormData();
        formData.append("file", file);
        try {
            const res = await fetch("/api/chats/upload", {
                method: "POST",
                body: formData,
            });
            const data = await res.json();
            pendingAttachments = [...pendingAttachments, data];
        } catch (err) {
            console.error("Upload failed:", err);
        }
    }

    function removeAttachment(fileId: string) {
        pendingAttachments = pendingAttachments.filter(
            (a) => a.file_id !== fileId,
        );
    }
</script>

<div class="bg-background mb-10">
    <div
        class="relative flex flex-col border rounded-xl bg-background focus-within:ring-1 focus-within:ring-ring transition-all duration-200"
        role="region"
        aria-label="Chat input drop zone"
        ondragenter={handleDragEnter}
        ondragover={handleDragOver}
        ondragleave={handleDragLeave}
        ondrop={handleDrop}
    >
        {#if isDragging}
            <div
                class="absolute inset-0 z-50 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm border-2 border-dashed border-primary rounded-xl pointer-events-none animate-in fade-in duration-200"
            >
                <Upload class="h-8 w-8 text-primary mb-2 animate-bounce" />
                <p class="text-sm font-medium text-primary">Drop files here</p>
            </div>
        {/if}

        {#if pendingAttachments.length > 0}
            <div class="flex flex-wrap gap-2 px-4 pt-4 pb-0">
                {#each pendingAttachments as att}
                    <Attachment
                        attachment={att}
                        onRemove={() => removeAttachment(att.file_id)}
                    />
                {/each}
            </div>
        {/if}

        <Textarea
            bind:value={input}
            placeholder="Type your message..."
            class="min-h-[120px] max-h-[300px] resize-none border-0 focus-visible:ring-0 shadow-none px-4 pt-4"
            onkeydown={handleKeydown}
            onpaste={handlePaste}
        />

        <div class="flex items-center justify-between gap-4 p-2">
            <div class="flex items-center gap-1">
                <Button
                    variant="ghost"
                    size="icon"
                    onclick={() => fileInput.click()}
                    title="Attach files"
                    class="h-8 w-8"
                >
                    <Paperclip class="h-4 w-4" />
                </Button>
                <input
                    type="file"
                    multiple
                    class="hidden"
                    bind:this={fileInput}
                    onchange={onFileChange}
                />

                <div class="flex items-center space-x-2 px-2 py-1 h-8">
                    <BrainCircuit class="h-3.5 w-3.5 text-muted-foreground" />
                    <Label
                        for="reasoning-toggle"
                        class="text-[10px] font-medium cursor-pointer text-muted-foreground uppercase tracking-wider"
                        >Reasoning</Label
                    >
                    <Switch
                        id="reasoning-toggle"
                        bind:checked={$enableReasoning}
                        class="scale-75"
                    />
                </div>
            </div>

            <div class="flex items-center gap-2">
                <Select.Root
                    type="single"
                    value={$selectedModel}
                    onValueChange={(v) => selectedModel.set(v)}
                >
                    <Select.Trigger
                        size="sm"
                        class="gap-1.5 px-2 font-medium text-xs bg-muted/30 border-0"
                    >
                        <Cpu class="h-3.5 w-3.5 text-muted-foreground" />
                        <Select.Value placeholder="Select model" />
                    </Select.Trigger>
                    <Select.Content>
                        <Select.Group>
                            {#each $models as m}
                                <Select.Item value={m} label={m} />
                            {/each}
                        </Select.Group>
                    </Select.Content>
                </Select.Root>

                <Button
                    variant={$currentIsGenerating ? "destructive" : "default"}
                    size="icon"
                    onclick={handleSend}
                    disabled={!input.trim() &&
                        pendingAttachments.length === 0 &&
                        !$currentIsGenerating}
                    class="h-8 w-8"
                >
                    {#if $currentIsGenerating}
                        <Square class="h-3.5 w-3.5" />
                    {:else}
                        <Send class="h-3.5 w-3.5" />
                    {/if}
                </Button>
            </div>
        </div>
    </div>
</div>
