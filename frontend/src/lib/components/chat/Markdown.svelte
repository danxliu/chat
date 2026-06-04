<script lang="ts">
	import { Marked } from 'marked';
	import markedKatex from 'marked-katex-extension';
	import { gfmHeadingId } from 'marked-gfm-heading-id';
	import { mangle } from 'marked-mangle';
	import DOMPurify from 'dompurify';
	import 'katex/dist/katex.min.css';

	let { content = '' } = $props();

	const marked = new Marked(
		markedKatex({
			throwOnError: false,
			displayMode: false
		}),
		gfmHeadingId(),
		mangle()
	);

	const html = $derived.by(() => {
		const rawHtml = marked.parse(content) as string;
		return DOMPurify.sanitize(rawHtml);
	});
</script>

<div class="markdown-body max-w-none">
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
	:global(.markdown-body h1) {
		font-size: 1.5rem;
		font-weight: 700;
		margin-top: 1.5rem;
		margin-bottom: 1rem;
	}
	:global(.markdown-body h2) {
		font-size: 1.25rem;
		font-weight: 600;
		margin-top: 1.25rem;
		margin-bottom: 0.75rem;
	}
	:global(.markdown-body h3) {
		font-size: 1.125rem;
		font-weight: 600;
		margin-top: 1rem;
		margin-bottom: 0.5rem;
	}
	:global(.markdown-body ul) {
		list-style-type: disc;
		margin-bottom: 1rem;
		padding-left: 1.5rem;
	}
	:global(.markdown-body ol) {
		list-style-type: decimal;
		margin-bottom: 1rem;
		padding-left: 1.5rem;
	}
	:global(.markdown-body li) {
		margin-bottom: 0.25rem;
	}
	:global(.markdown-body table) {
		width: 100%;
		border-collapse: collapse;
		margin-top: 1rem;
		margin-bottom: 1rem;
	}
	:global(.markdown-body th), :global(.markdown-body td) {
		border: 1px solid hsl(var(--border));
		padding: 0.5rem;
		text-align: left;
	}
	:global(.markdown-body th) {
		background-color: hsl(var(--muted));
		font-weight: 600;
	}
	:global(.markdown-body tr:nth-child(even)) {
		background-color: hsl(var(--muted) / 0.5);
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
