<script lang="ts">
    import * as Dialog from "$lib/components/ui/dialog";
    import { Button } from "$lib/components/ui/button";
    import { Input } from "$lib/components/ui/input";
    import { Label } from "$lib/components/ui/label";
    import { settings, backendDefaults } from "$lib/stores/settings";
    import { Settings as SettingsIcon } from "lucide-svelte";

    let open = $state(false);
</script>

<Dialog.Root bind:open>
    <Dialog.Trigger class="w-full">
        <Button
            variant="ghost"
            size="sm"
            class="w-full justify-start gap-2 text-muted-foreground"
        >
            <SettingsIcon class="h-4 w-4" />
            Settings
        </Button>
    </Dialog.Trigger>
    <Dialog.Content class="sm:max-w-[425px]">
        <Dialog.Header>
            <Dialog.Title>Settings</Dialog.Title>
        </Dialog.Header>
        <div class="grid gap-4 py-4">
            <div class="grid gap-2">
                <Label for="llmModel">LLM Model Name</Label>
                <Input
                    id="llmModel"
                    bind:value={$settings.llmModel}
                    placeholder={$backendDefaults?.llm_model || "e.g. gpt-4o"}
                />
            </div>
            <div class="grid gap-2">
                <Label for="llmBaseUrl">LLM API Base URL</Label>
                <Input
                    id="llmBaseUrl"
                    bind:value={$settings.llmBaseUrl}
                    placeholder={$backendDefaults?.llm_api_base || "e.g. http://localhost:11434/v1"}
                />
            </div>
            <hr class="border-muted" />
            <div class="grid gap-2">
                <Label for="embedModel">Embedding Model Name</Label>
                <Input
                    id="embedModel"
                    bind:value={$settings.embedModel}
                    placeholder={$backendDefaults?.embedding_model || "e.g. text-embedding-3-small"}
                />
            </div>
            <div class="grid gap-2">
                <Label for="embedBaseUrl">Embedding API Base URL</Label>
                <Input
                    id="embedBaseUrl"
                    bind:value={$settings.embedBaseUrl}
                    placeholder={$backendDefaults?.embed_api_base || "e.g. http://localhost:8080/v1"}
                />
            </div>
        </div>
        <Dialog.Footer>
            <Button type="button" onclick={() => (open = false)}>Close</Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
