<script lang="ts">
	import { marked } from 'marked';
	import markedKatex from 'marked-katex-extension';
	import DOMPurify from 'dompurify';
	import 'katex/dist/katex.min.css';

	let { content = '' } = $props();

	// Configure marked with katex extension
	marked.use(markedKatex({
		throwOnError: false,
		displayMode: false
	}));

	const html = $derived.by(() => {
		const rawHtml = marked.parse(content) as string;
		return DOMPurify.sanitize(rawHtml);
	});
</script>

<div class="markdown-body prose prose-slate max-w-none dark:prose-invert">
	{@html html}
</div>

<style>
	:global(.markdown-body pre) {
		background-color: hsl(var(--muted));
		padding: 1rem;
		border-radius: 0.5rem;
		overflow-x: auto;
		margin-top: 1rem;
		margin-bottom: 1rem;
	}
	:global(.markdown-body code) {
		background-color: hsl(var(--muted));
		padding: 0.125rem 0.25rem;
		border-radius: 0.25rem;
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
		font-size: 0.875rem;
	}
	:global(.markdown-body p) {
		margin-bottom: 1rem;
	}
	:global(.markdown-body p:last-child) {
		margin-bottom: 0;
	}
	:global(.markdown-body ul, .markdown-body ol) {
		margin-bottom: 1rem;
		padding-left: 1.5rem;
	}
	:global(.markdown-body li) {
		margin-bottom: 0.25rem;
	}
	:global(.markdown-body blockquote) {
		border-left-width: 4px;
		border-left-color: hsl(var(--primary));
		padding-left: 1rem;
		font-style: italic;
		margin-top: 1rem;
		margin-bottom: 1rem;
	}
</style>
