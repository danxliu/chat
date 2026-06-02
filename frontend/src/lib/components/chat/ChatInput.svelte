<script lang="ts">
	import { 
		sendMessage, 
		isGenerating, 
		cancelGeneration, 
		models, 
		selectedModel, 
		enableReasoning 
	} from '$lib/stores/chat';
	import { Button } from '$lib/components/ui/button';
	import { Textarea } from '$lib/components/ui/textarea';
	import { 
		Select, 
		SelectContent, 
		SelectItem, 
		SelectTrigger, 
		SelectValue 
	} from '$lib/components/ui/select';
	import { Switch } from '$lib/components/ui/switch';
	import { Label } from '$lib/components/ui/label';
	import { 
		Send, 
		Square, 
		Paperclip, 
		BrainCircuit,
		X
	} from 'lucide-svelte';
	import type { Attachment as AttachmentType } from '$lib/stores/chat';
	import Attachment from './Attachment.svelte';

	let input = $state('');
	let pendingAttachments = $state<AttachmentType[]>([]);
	let fileInput: HTMLInputElement;

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSend();
		}
	}

	async function handleSend() {
		if ($isGenerating) {
			cancelGeneration();
			return;
		}

		if (input.trim() || pendingAttachments.length > 0) {
			sendMessage(input, [...pendingAttachments]);
			input = '';
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
		target.value = '';
	}

	async function uploadFile(file: File) {
		const formData = new FormData();
		formData.append('file', file);
		try {
			const res = await fetch('/api/chats/upload', {
				method: 'POST',
				body: formData
			});
			const data = await res.json();
			pendingAttachments = [...pendingAttachments, data];
		} catch (err) {
			console.error('Upload failed:', err);
		}
	}

	function removeAttachment(fileId: string) {
		pendingAttachments = pendingAttachments.filter(a => a.file_id !== fileId);
	}
</script>

<div class="p-4 bg-background">
	<div class="flex flex-col border rounded-xl bg-background focus-within:ring-1 focus-within:ring-ring transition-all duration-200">
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
			class="min-h-[80px] max-h-[200px] resize-none border-0 focus-visible:ring-0 shadow-none px-4 pt-4"
			onkeydown={handleKeydown}
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
					<Label for="reasoning-toggle" class="text-[10px] font-medium cursor-pointer text-muted-foreground uppercase tracking-wider">Reasoning</Label>
					<Switch 
						id="reasoning-toggle" 
						bind:checked={$enableReasoning}
						class="scale-75"
					/>
				</div>
			</div>

			<div class="flex items-center gap-2">
				<Select type="single" bind:value={$selectedModel}>
					<SelectTrigger class="w-[200px] h-8 text-xs border-0 bg-muted/50 focus:ring-0">
						<SelectValue placeholder="Select model" />
					</SelectTrigger>
					<SelectContent>
						{#each $models as model}
							<SelectItem value={model} label={model} class="text-xs">{model}</SelectItem>
						{/each}
					</SelectContent>
				</Select>

				<Button 
					variant={$isGenerating ? "destructive" : "default"}
					size="icon"
					onclick={handleSend}
					disabled={!input.trim() && pendingAttachments.length === 0 && !$isGenerating}
					class="h-8 w-8"
				>
					{#if $isGenerating}
						<Square class="h-3.5 w-3.5" />
					{:else}
						<Send class="h-3.5 w-3.5" />
					{/if}
				</Button>
			</div>
		</div>
	</div>
</div>
