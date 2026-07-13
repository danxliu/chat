<script lang="ts">
	import { Marked } from 'marked';
	import markedKatex from 'marked-katex-extension';
	import { gfmHeadingId } from 'marked-gfm-heading-id';
	import { mangle } from 'marked-mangle';
	import DOMPurify from 'dompurify';
	import 'katex/dist/katex.min.css';

	let { content = '' } = $props();

	const citationExtension = {
		name: 'citation',
		level: 'inline',
		start(src: string) { return src.match(/\[cite:/)?.index; },
		tokenizer(src: string) {
			const rule = /^\[cite:([^\]]+)\]\(([^)]+)\)/;
			const match = rule.exec(src);
			if (match) {
				return {
					type: 'citation',
					raw: match[0],
					text: match[1],
					href: match[2]
				};
			}
		},
		renderer(token: any) {
			return `<a href="${token.href}" target="_blank" rel="noopener noreferrer" class="citation-pill">${token.text}</a>`;
		}
	};

	const marked = new Marked(
		markedKatex({
			throwOnError: false,
			displayMode: false
		}),
		gfmHeadingId(),
		mangle()
	);
	marked.use({ extensions: [citationExtension] });

	const html = $derived.by(() => {
		const rawHtml = marked.parse(content) as string;
		return DOMPurify.sanitize(rawHtml, { ADD_ATTR: ['target'] });
	});
</script>

<div class="markdown-body max-w-none flex flex-col gap-4">
	{@html html}
</div>

<style>
	:global(.markdown-body pre) {
		background-color: var(--muted);
		padding: 1rem;
		border-radius: 0.5rem;
		overflow-x: auto;
	}
	:global(.markdown-body code) {
		background-color: var(--muted);
		padding: 0.125rem 0.25rem;
		border-radius: 0.25rem;
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
		font-size: 0.875rem;
	}
	:global(.markdown-body h1) {
		font-size: 1.5rem;
		font-weight: 700;
	}
	:global(.markdown-body h2) {
		font-size: 1.25rem;
		font-weight: 600;
	}
	:global(.markdown-body h3) {
		font-size: 1.125rem;
		font-weight: 600;
	}
	:global(.markdown-body ul) {
		list-style-type: disc;
		padding-left: 1.5rem;
	}
	:global(.markdown-body ol) {
		list-style-type: decimal;
		padding-left: 1.5rem;
	}
	:global(.markdown-body li) {
		margin-bottom: 0.25rem;
	}
	:global(.markdown-body table) {
		width: 100%;
		border-collapse: collapse;
	}
	:global(.markdown-body th), :global(.markdown-body td) {
		border: 1px solid var(--border);
		padding: 0.5rem;
		text-align: left;
	}
	:global(.markdown-body th) {
		background-color: var(--muted);
		font-weight: 600;
	}
	:global(.markdown-body tr:nth-child(even)) {
		background-color: color-mix(in srgb, var(--muted) 50%, transparent);
	}
	:global(.markdown-body blockquote) {
		border-left-width: 4px;
		border-left-color: var(--primary);
		padding-left: 1rem;
		font-style: italic;
	}
	:global(.markdown-body hr) {
		border: 0;
		border-top: 1px solid var(--border);
	}
	:global(.markdown-body a:not(.citation-pill)) {
		color: var(--primary);
		text-decoration: underline;
		text-underline-offset: 4px;
	}
	:global(.markdown-body .citation-pill) {
		display: inline-flex;
		align-items: center;
		padding: 0.125rem 0.5rem;
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--primary-foreground);
		background-color: var(--primary);
		border-radius: 9999px;
		text-decoration: none;
		margin-left: 0.25rem;
		opacity: 0.85;
		transition: opacity 0.2s ease;
		vertical-align: middle;
	}
	:global(.markdown-body .citation-pill:hover) {
		opacity: 1;
	}
</style>
