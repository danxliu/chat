<script lang="ts">
    import { userUUID, importUUID } from "$lib/stores/user";
    import { toast } from "svelte-sonner";
    import * as Dialog from "$lib/components/ui/dialog";
    import { Button } from "$lib/components/ui/button";
    import { Input } from "$lib/components/ui/input";
    import { Label } from "$lib/components/ui/label";
    import { Separator } from "$lib/components/ui/separator";
    import { Copy, Check, User, Import } from "lucide-svelte";
    import { get } from "svelte/store";

    let {
        open = $bindable(false),
        onImported = () => {},
    }: {
        open: boolean;
        onImported?: () => void;
    } = $props();

    let importInput = $state("");
    let hasCopied = $state(false);
    let isImporting = $state(false);

    async function handleCopy() {
        try {
            await navigator.clipboard.writeText(get(userUUID));
            hasCopied = true;
            setTimeout(() => (hasCopied = false), 2000);
        } catch {
            toast.error("Failed to copy to clipboard");
        }
    }

    function handleImport() {
        if (!importInput.trim()) {
            toast.error("Please enter a UUID to import.");
            return;
        }

        isImporting = true;
        const success = importUUID(importInput);

        if (success) {
            toast.success("UUID imported successfully. Reloading your data...");
            importInput = "";
            open = false;
            onImported();
        } else {
            toast.error(
                "Invalid UUID format. Expected format: 550e8400-e29b-41d4-a716-446655440000",
            );
        }
        isImporting = false;
    }
</script>

<Dialog.Root bind:open>
    <Dialog.Content class="sm:max-w-md">
        <Dialog.Header>
            <Dialog.Title class="flex items-center gap-2">
                <User class="h-5 w-5" />
                User Settings
            </Dialog.Title>
            <Dialog.Description>
                Your user ID links your chats and memories. You can copy it to
                use on another device.
            </Dialog.Description>
        </Dialog.Header>

        <div class="space-y-4 py-4">
            <div class="space-y-2">
                <Label for="current-uuid">Your User ID</Label>
                <div class="flex gap-2">
                    <Input
                        id="current-uuid"
                        value={get(userUUID)}
                        readonly
                        class="font-mono text-xs"
                    />
                    <Button
                        variant="outline"
                        size="icon"
                        onclick={handleCopy}
                        title="Copy to clipboard"
                    >
                        {#if hasCopied}
                            <Check class="h-4 w-4 text-green-500" />
                        {:else}
                            <Copy class="h-4 w-4" />
                        {/if}
                    </Button>
                </div>
                <p class="text-xs text-muted-foreground">
                    Copy this ID and paste it on another device to access the
                    same chats and memories.
                </p>
            </div>

            <Separator />

            <div class="space-y-2">
                <Label for="import-uuid">Import UUID</Label>
                <p class="text-xs text-muted-foreground">
                    Paste a UUID from another device to access your chats and
                    memories here.
                </p>
                <Input
                    id="import-uuid"
                    bind:value={importInput}
                    placeholder="550e8400-e29b-41d4-a716-446655440000"
                    class="font-mono text-xs"
                />
                <Button
                    variant="outline"
                    class="w-full gap-2"
                    onclick={handleImport}
                    disabled={isImporting || !importInput.trim()}
                >
                    <Import class="h-4 w-4" />
                    Import
                </Button>
            </div>
        </div>

        <Dialog.Footer>
            <Dialog.Close>
                <Button variant="ghost">Close</Button>
            </Dialog.Close>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
