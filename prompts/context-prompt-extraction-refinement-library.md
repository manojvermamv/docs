# User-Prompt Extraction & Refinement Library

A prompt system for scanning chat/session/workspace context, locating every prompt the user gave, and producing a polished, production-ready prompt library in Markdown. Two approaches are included:

- **Monolithic version** — one self-contained, fire-and-forget prompt. No assembly required.
- **Modular version** — a shared Core + swappable Mode Blocks, for when you already know the extraction type.

See [When to Use Which](#when-to-use-which) before picking one.

---

## Monolithic Version (self-contained, no assembly)

Use this as a single drop-in prompt. It handles messy sessions — iterative rewrites, mid-conversation corrections, abandoned drafts — and degrades gracefully regardless of how the original prompts were phrased or scattered.

```
Scan the entire available chat/session/workspace context and identify every prompt, instruction, or directive the user wrote — not the assistant's responses, paraphrases, or suggestions. For each prompt found: (1) extract the final, most refined version, treating later revisions and corrections as authoritative over earlier drafts; (2) clean wording errors, grammatical inconsistencies, and structural ambiguities without altering meaning, intent, or scope; (3) discard intermediate drafts, partial rewrites, and abandoned iterations unless they contain distinct intent not present in the final version; (4) consolidate near-identical or iteratively refined prompts on the same topic into a single unified prompt, noting how many iterations it went through. Do not invent instructions, constraints, or intent that were not present or confirmed in the source context — flag any gap you filled with a reasonable inference using [ASSUMED]. Preserve the original meaning, scope, and nuance of each prompt rather than paraphrasing away important constraints or detail. Resolve contradictions between iterations by treating the most recently confirmed version as authoritative and noting the earlier conflicting version in a short callout. Organize the output as a clean Markdown prompt library: give each prompt a descriptive title, one-line purpose statement, the refined prompt in a fenced code block, and optional usage notes — ordered by topic or workflow sequence where discernible, otherwise by first appearance in the conversation. The output must stand alone: a reader with no access to the original conversation must be able to understand and use every prompt without additional context.
```

### When and where to use the Monolithic version

**Use it when:**
- The session contains **iterative prompt rewrites** — the user kept refining the same prompt across multiple messages
- Prompts are **scattered and interleaved** with other discussion, not grouped together
- You are **not sure in advance** how many distinct prompts exist or how they relate
- It is a **one-off extraction task** — not worth the overhead of assembling Core + Mode
- The session mixes **corrections, wording fixes, and intent changes** mid-conversation
- You are handing this prompt to someone else (teammate, template, automation) who cannot self-diagnose the right mode

**Avoid it when:**
- All prompts are already clean, final, and clearly delineated — the generic fallback clauses add unnecessary overhead
- You need **tight structural control** over output format (e.g. always output as a numbered registry, always version-stamp every prompt)
- Prompt length or token budget is a hard constraint and you know exactly which mode you need

**Rule of thumb:** if the session has more than one iteration of the same prompt, or if any prompt was delivered across multiple messages, use Monolithic.

---

## Modular Version

### Core (always include)

```
Scan the entire available chat/session/workspace context and identify every prompt, instruction, or directive the user wrote — not the assistant's responses, paraphrases, or suggestions. For each prompt: extract the final, most refined version treating later revisions as authoritative over earlier drafts; clean wording errors and structural ambiguities without altering meaning or scope; discard intermediate drafts unless they contain distinct intent absent from the final version; consolidate near-identical prompts on the same topic into one unified prompt; and flag any inference you made with [ASSUMED]. Do not invent instructions or intent not present in the source context. [MODE BLOCK GOES HERE] The output must stand alone: a reader with no access to the original conversation must be able to understand and use every prompt without additional context.
```

---

## Mode Blocks

### 1. Final-State Library
Use for: clean extraction when you only need the latest, best version of each prompt — no history, no versioning.

```
Output each prompt as a titled entry with a one-line purpose statement and the refined prompt in a fenced code block. Include short usage notes only where the prompt has non-obvious constraints or preconditions. Order by topic or workflow sequence where discernible, otherwise by first appearance. Omit all iteration history and draft commentary.
```

### 2. Versioned Registry
Use for: audits, changelogs, or handoffs where the evolution of each prompt matters as much as the final output.

```
For each prompt, output a versioned registry entry: title, one-line purpose, iteration count (e.g. v1 → v3), a collapsed diff summary noting what changed across iterations, and the final refined version in a fenced code block. Flag the final version explicitly with a `[FINAL]` marker. Where a draft was abandoned mid-revision, note it as `[ABANDONED at v{n}: reason if stated]`.
```

### 3. Categorized Library
Use for: sessions containing many distinct prompt types (system prompts, one-shot prompts, loop prompts, meta-prompts) that benefit from grouping.

```
Group prompts by type or functional category (e.g. System Prompts, Loop / Finding Prompts, Structural Analysis Prompts, Meta / Context Prompts). Within each group, order by first appearance. Give each category a short section header and one-sentence description of what the prompts in it are for. Each prompt entry: title, one-line purpose, refined prompt in a fenced code block, and optional usage notes.
```

### 4. Unified / Consolidated Master
Use for: sessions where multiple related prompts should be merged into one master prompt rather than kept as separate entries.

```
Identify clusters of related prompts that share a common goal or pipeline stage. For each cluster, merge all constituent prompts into a single unified prompt that captures the union of their intent, constraints, and scope — without redundancy. Title the merged prompt to reflect its combined purpose. Note which original prompts were merged and what each contributed. Where prompts are genuinely independent (different goals, different targets), keep them separate.
```

### 5. README / Handoff Format
Use for: exporting prompts as a self-contained reference document intended for teammates, automation pipelines, or external use.

```
Produce a README-style document: open with a one-paragraph summary of what this prompt collection covers and when to use it. Then present each prompt as a titled section with purpose, preconditions or requirements, the refined prompt in a fenced code block, and a concrete usage example showing the prompt in context. Close with a "When to Use Which" table mapping use cases to prompt names. Assume the reader has never seen the original session.
```

---

## Assembly Examples

### Example A — Final-State Library mode

```
Scan the entire available chat/session/workspace context and identify every prompt, instruction, or directive the user wrote — not the assistant's responses, paraphrases, or suggestions. For each prompt: extract the final, most refined version treating later revisions as authoritative over earlier drafts; clean wording errors and structural ambiguities without altering meaning or scope; discard intermediate drafts unless they contain distinct intent absent from the final version; consolidate near-identical prompts on the same topic into one unified prompt; and flag any inference you made with [ASSUMED]. Do not invent instructions or intent not present in the source context. Output each prompt as a titled entry with a one-line purpose statement and the refined prompt in a fenced code block. Include short usage notes only where the prompt has non-obvious constraints or preconditions. Order by topic or workflow sequence where discernible, otherwise by first appearance. Omit all iteration history and draft commentary. The output must stand alone: a reader with no access to the original conversation must be able to understand and use every prompt without additional context.
```

### Example B — Versioned Registry mode

```
Scan the entire available chat/session/workspace context and identify every prompt, instruction, or directive the user wrote — not the assistant's responses, paraphrases, or suggestions. For each prompt: extract the final, most refined version treating later revisions as authoritative over earlier drafts; clean wording errors and structural ambiguities without altering meaning or scope; discard intermediate drafts unless they contain distinct intent absent from the final version; consolidate near-identical prompts on the same topic into one unified prompt; and flag any inference you made with [ASSUMED]. Do not invent instructions or intent not present in the source context. For each prompt, output a versioned registry entry: title, one-line purpose, iteration count (e.g. v1 → v3), a collapsed diff summary noting what changed across iterations, and the final refined version in a fenced code block. Flag the final version explicitly with a [FINAL] marker. Where a draft was abandoned mid-revision, note it as [ABANDONED at v{n}: reason if stated]. The output must stand alone: a reader with no access to the original conversation must be able to understand and use every prompt without additional context.
```

### Example C — README / Handoff mode

```
Scan the entire available chat/session/workspace context and identify every prompt, instruction, or directive the user wrote — not the assistant's responses, paraphrases, or suggestions. For each prompt: extract the final, most refined version treating later revisions as authoritative over earlier drafts; clean wording errors and structural ambiguities without altering meaning or scope; discard intermediate drafts unless they contain distinct intent absent from the final version; consolidate near-identical prompts on the same topic into one unified prompt; and flag any inference you made with [ASSUMED]. Do not invent instructions or intent not present in the source context. Produce a README-style document: open with a one-paragraph summary of what this prompt collection covers and when to use it. Then present each prompt as a titled section with purpose, preconditions or requirements, the refined prompt in a fenced code block, and a concrete usage example showing the prompt in context. Close with a "When to Use Which" table mapping use cases to prompt names. Assume the reader has never seen the original session. The output must stand alone: a reader with no access to the original conversation must be able to understand and use every prompt without additional context.
```

---

## Notes on Design Choices

- **User-only extraction** — explicitly targets the user's messages only; prevents the assistant's suggestions, restatements, or paraphrases from being mistakenly captured as the user's prompts.
- **Revision authority rule** — later revisions override earlier drafts deterministically; avoids merging conflicting versions silently.
- **Distinct-intent preservation** — abandoned drafts are discarded *unless* they contain intent not carried forward; prevents silent loss of scope that the user may have intentionally kept from an earlier version.
- **Anti-hallucination guardrail** — forbids inventing constraints, instructions, or intent not present or confirmed in context.
- **Assumption flagging** — any inference used to fill a gap must be marked `[ASSUMED]`, not presented as fact.
- **Consolidation rule** — near-identical or iteratively refined prompts on the same topic collapse into one unified entry rather than producing duplicate or near-duplicate library entries.
- **Audience-independence bar** — output must stand alone, fully usable by a reader with no access to the original conversation.
- **Purposeful formatting** — fenced code blocks, titles, and usage notes used where they aid usability; no decorative structure.

---

## How to Use

**Modular version:**
1. Copy the **Core** block.
2. Pick the **Mode Block** that matches your output type (or lightly blend two, e.g. Categorized Library + Versioned Registry for a categorized changelog).
3. Paste the mode block in place of `[MODE BLOCK GOES HERE]`.
4. Run it against your chat/session context.

**Monolithic version:**
1. Copy the single self-contained prompt as-is.
2. Run it directly — no assembly needed.

---

## When to Use Which

| Situation | Recommended |
|---|---|
| Prompts are scattered across the session, mixed with discussion | **Monolithic** |
| The same prompt was refined multiple times across messages | **Monolithic** |
| You need only the final clean version of each prompt, no history | **Modular — Final-State Library** |
| Audit or handoff where evolution of each prompt matters | **Modular — Versioned Registry** |
| Session has many distinct prompt types (system, loop, meta, structural) | **Modular — Categorized Library** |
| Related prompts should merge into one master prompt | **Modular — Unified / Consolidated Master** |
| Output is going to a teammate or pipeline with no session access | **Modular — README / Handoff Format** |
| One-off extraction, uncertain how many prompts exist or how they relate | **Monolithic** |
| Token budget is tight and extraction type is certain | **Modular** |

**Note:** the Modular Core deliberately omits the fidelity/nuance clause and the generic structure fallback — those live only in the Monolithic version. This keeps the Modular version composable and lean for known, well-defined extraction tasks, but less resilient on chaotic or iterative sessions. That is a deliberate tradeoff, not an oversight.
