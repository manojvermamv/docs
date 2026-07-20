# prompts/ — Prompt Templates

## Purpose

Owns reusable prompt templates for code analysis, architecture auditing, TA indicator generation, context-to-markdown conversion, and general auditing workflows.

## Ownership

| File | Lines | Domain |
|------|-------|--------|
| `UNIFIED_ITERATIVE_ANALYSIS_PROMPT.md` | 361 | Multi-phase code audit with fix tracking and graph-based understanding |
| `OPENALGO_TA_ANALYSIS_PROMPT.md` | 466 | OpenAlgo TA indicator analysis — PineScript-equivalent, bar-by-bar, multi-timeframe |
| `context-to-markdown-prompt-library.md` | 142 | Session/context → polished Markdown document (monolithic + modular) |
| `general-prompts.md` | 112 | Source-grounded cross-check loop, online auditing, general-use prompts |

## Local Contracts

- Every prompt is self-contained — no file depends on another
- Each prompt file may contain multiple prompt variants separated by headings
- Prompts may reference external repositories (GitHub URLs) — those repos are the source of truth
- No prompt modifies files; all are read-only templates for agent consumption

## Work Guidance

- Use `UNIFIED_ITERATIVE_ANALYSIS_PROMPT.md` for architecture audits and iterative fix-tracking across conversation turns
- Use `OPENALGO_TA_ANALYSIS_PROMPT.md` when working with OpenAlgo TA indicators (PineScript equivalents, bar-by-bar semantics)
- Use `context-to-markdown-prompt-library.md` when converting session/workspace context into polished Markdown
- Use `general-prompts.md` for source-grounded cross-check loops against OpenAlgo repos

## Verification

- No automated verification exists for prompt files
- Manual review: ensure prompts are self-contained, reference correct URLs, and maintain consistent heading structure

## Child DOX Index

No child directories.
