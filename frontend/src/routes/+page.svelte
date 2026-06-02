<script lang="ts">
	import { onMount } from 'svelte';
	import { 
		connectWebSocket, 
		refreshSessions, 
		loadModels, 
		messages, 
		currentSessionId,
		sessions,
		switchSession,
		createNewSession
	} from '$lib/stores/chat';
	import Sidebar from '$lib/components/chat/Sidebar.svelte';
	import ChatMessage from '$lib/components/chat/ChatMessage.svelte';
	import ChatInput from '$lib/components/chat/ChatInput.svelte';
	import { MessageSquare, Sun, Moon } from 'lucide-svelte';
	import { get } from 'svelte/store';
	import { mode, toggleMode } from 'mode-watcher';
	import { Button } from '$lib/components/ui/button';

	let scrollAreaViewport = $state<HTMLElement | null>(null);

	onMount(async () => {
		connectWebSocket();
		await refreshSessions();
		await loadModels();

		const s = get(sessions);
		if (s.length > 0) {
			await switchSession(s[0].session_id);
		} else {
			await createNewSession();
		}
	});

	// Auto-scroll to bottom when messages change
	$effect(() => {
		if ($messages && scrollAreaViewport) {
			const viewport = scrollAreaViewport;
			setTimeout(() => {
				viewport.scrollTo({
					top: viewport.scrollHeight,
					behavior: 'smooth'
				});
			}, 100);
		}
	});
</script>

<div class="flex h-screen w-full overflow-hidden bg-background">
	<aside class="w-64 shrink-0 h-full">
		<Sidebar />
	</aside>

	<main class="flex-1 flex flex-col h-full relative overflow-hidden">
		<header class="h-14 border-b flex items-center justify-between px-6 bg-background/95 backdrop-blur shrink-0">
			<h1 class="font-semibold text-sm">
				{#if $currentSessionId}
					{$sessions.find(s => s.session_id === $currentSessionId)?.title || 'New Chat'}
				{:else}
					Select a chat
				{/if}
			</h1>

			<Button variant="ghost" size="icon" onclick={toggleMode}>
				{#if mode.current === 'dark'}
					<Moon class="h-4 w-4" />
				{:else}
					<Sun class="h-4 w-4" />
				{/if}
				<span class="sr-only">Toggle theme</span>
			</Button>
		</header>

		<div 
			class="flex-1 overflow-y-auto min-h-0 p-4 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden" 
			bind:this={scrollAreaViewport}
		>
			<div class="max-w-4xl mx-auto flex flex-col min-h-full">
				{#each $messages as message}
					<ChatMessage {message} />
				{/each}
				
				{#if $messages.length === 0}
					<div class="flex-1 flex flex-col items-center justify-center text-muted-foreground gap-4 opacity-50">
						<div class="rounded-full bg-muted p-4">
							<MessageSquare class="h-8 w-8 text-muted-foreground" />
						</div>
						<p class="text-sm font-medium">How can I help you today?</p>
					</div>
				{/if}
			</div>
		</div>

		<div class="max-w-4xl w-full mx-auto shrink-0">
			<ChatInput />
		</div>
	</main>
</div>

<style>
	:global(html, body) {
		height: 100%;
		overflow: hidden;
	}
</style>
