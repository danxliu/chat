<script lang="ts">
	import type { Attachment as AttachmentType } from '$lib/stores/chat';
	import { truncateMiddle } from '$lib/utils';
	import { FileText, X } from 'lucide-svelte';
	import { Button } from '$lib/components/ui/button';

	interface Props {
		attachment: AttachmentType;
		onRemove?: () => void;
	}

	let { attachment, onRemove }: Props = $props();

	const isImage = $derived(attachment.mime_type.startsWith('image/'));
	const imageUrl = $derived(`/uploads/${attachment.stored_filename}`);
</script>

<div class="relative group w-20 h-20 rounded-lg border bg-muted overflow-hidden flex flex-col items-center justify-center text-center p-1 shadow-sm">
	{#if isImage}
		<img 
			src={imageUrl} 
			alt={attachment.filename} 
			class="absolute inset-0 w-full h-full object-cover"
		/>
	{:else}
		<FileText class="h-8 w-8 text-muted-foreground mb-1" />
		<span class="text-[10px] leading-tight text-muted-foreground break-all px-1">
			{truncateMiddle(attachment.filename, 12)}
		</span>
	{/if}

	{#if onRemove}
		<button
			onclick={onRemove}
			class="absolute top-1 right-1 p-0.5 rounded-full bg-background/80 text-foreground opacity-0 group-hover:opacity-100 transition-opacity hover:bg-destructive hover:text-destructive-foreground"
			title="Remove attachment"
		>
			<X class="h-3 w-3" />
		</button>
	{/if}
</div>
