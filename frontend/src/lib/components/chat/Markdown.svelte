<script lang="ts">
    import { Marked } from "marked";
    import markedKatex from "marked-katex-extension";
    import { markedHighlight } from "marked-highlight";
    import hljs from "highlight.js";
    import { gfmHeadingId } from "marked-gfm-heading-id";
    import { mangle } from "marked-mangle";
    import DOMPurify from "dompurify";
    import "katex/dist/katex.min.css";
    import "highlight.js/styles/github-dark.min.css";

    let { content = "", isUser = false } = $props();

    const citationExtension = {
        name: "citation",
        level: "inline",
        start(src: string) {
            return src.match(/\[cite:/)?.index;
        },
        tokenizer(src: string) {
            const rule = /^\[cite:([^\]]+)\]\(([^)]+)\)/;
            const match = rule.exec(src);
            if (match) {
                return {
                    type: "citation",
                    raw: match[0],
                    text: match[1],
                    href: match[2],
                };
            }
        },
        renderer(token: any) {
            return `<a href="${token.href}" target="_blank" rel="noopener noreferrer" class="citation-pill">${token.text}</a>`;
        },
    };

    const marked = new Marked(
        markedHighlight({
            langPrefix: "hljs language-",
            highlight(code, lang) {
                const language = hljs.getLanguage(lang) ? lang : "plaintext";
                return hljs.highlight(code, { language }).value;
            },
        }),
        markedKatex({
            throwOnError: false,
            displayMode: false,
        }),
        gfmHeadingId(),
        mangle(),
    );
    marked.use({ extensions: [citationExtension] });

    // Rewrite LaTeX delimiters before `marked` runs its escape pass so its
    // escape step doesn't strip the backslashes before the katex extension
    // sees them.  We also escape bare `$` (currency amounts, etc.) so they
    // aren't misinterpreted as inline-math delimiters by marked-katex.
    //
    // Fenced code blocks (``` … ```) and inline code (` … `) are skipped.
    function preprocessLatexDelimiters(src: string): string {
        return src.replace(
            /(```[\s\S]*?```|`[^`]+`)|\$|\\(\[|\]|\(|\))/g,
            (match, codeBlock, delimiter) => {
                // Leave code blocks / inline code untouched
                if (codeBlock) return codeBlock;
                // Bare dollar sign → escaped so marked renders it as literal $
                if (match === "$") return "\\$";
                // Swap LaTeX delimiters for marked-katex
                if (delimiter === "[" || delimiter === "]") return "$$";
                return "$";
            },
        );
    }

    const html = $derived.by(() => {
        const preprocessed = preprocessLatexDelimiters(content);
        const rawHtml = marked.parse(preprocessed) as string;
        return DOMPurify.sanitize(rawHtml, { ADD_ATTR: ["target"] });
    });
</script>

<div
    class="markdown-body max-w-none flex flex-col gap-4"
    class:is-user={isUser}
>
    {@html html}
</div>

<style>
    /* --- Code blocks & syntax highlighting --- */
    :global(.markdown-body pre) {
        background-color: var(--muted);
        padding: 1rem;
        border-radius: 0.5rem;
        overflow-x: auto;
    }
    :global(.markdown-body pre code) {
        background-color: transparent;
        padding: 0;
        border-radius: 0;
        font-size: 0.8125rem;
        line-height: 1.6;
    }
    :global(.markdown-body code) {
        background-color: var(--muted);
        padding: 0.125rem 0.25rem;
        border-radius: 0.25rem;
        font-family:
            ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
            "Liberation Mono", "Courier New", monospace;
        font-size: 0.875rem;
    }
    /* Override highlight.js theme background so it inherits from our pre */
    :global(.markdown-body pre code.hljs) {
        background: transparent;
    }

    /* --- Headings --- */
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

    /* --- Lists --- */
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

    /* --- Tables --- */
    :global(.markdown-body table) {
        width: 100%;
        border-collapse: collapse;
    }
    :global(.markdown-body th),
    :global(.markdown-body td) {
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

    /* --- Blockquotes --- */
    :global(.markdown-body blockquote) {
        border-left-width: 4px;
        border-left-color: var(--primary);
        padding-left: 1rem;
        font-style: italic;
    }

    /* --- Horizontal rules --- */
    :global(.markdown-body hr) {
        border: 0;
        border-top: 1px solid var(--border);
    }

    /* --- Links --- */
    :global(.markdown-body a:not(.citation-pill)) {
        color: var(--primary);
        text-decoration: underline;
        text-underline-offset: 4px;
    }

    /* --- Citations --- */
    :global(.markdown-body .citation-pill) {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.2em 0.45em;
        font-size: 0.75em;
        font-weight: 600;
        color: var(--primary-foreground);
        background-color: var(--primary);
        border-radius: 9999px;
        text-decoration: none;
        margin-left: 0.1em;
        opacity: 0.85;
        transition: opacity 0.2s ease;
        vertical-align: middle;
        line-height: 1;
        min-width: 1.6em;
        text-align: center;
        white-space: nowrap;
        position: relative;
        top: -0.05em;
    }
    :global(.markdown-body .citation-pill:hover) {
        opacity: 1;
    }

    /* --- KaTeX dark-mode fix --- */
    :global(.markdown-body .katex) {
        color: inherit;
    }
    :global(.markdown-body .katex .mfrac .frac-line) {
        border-color: currentColor;
    }
    :global(.markdown-body .katex .overline .overline-line),
    :global(.markdown-body .katex .underline .underline-line) {
        border-color: currentColor;
    }
    :global(.markdown-body .katex .sqrt > .sqrt-line) {
        border-color: currentColor;
    }
    :global(.markdown-body .katex .sqrt > .sqrt-sign) {
        color: inherit;
    }
</style>
