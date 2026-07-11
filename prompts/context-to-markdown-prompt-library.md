# Context-to-Markdown Prompt Library

A prompt system for turning chat/session/workspace context into a polished, production-quality Markdown document. Two approaches are included:

- **Monolithic version** — one self-contained, fire-and-forget prompt. No assembly required.
- **Modular version** — a shared Core + swappable Mode Blocks, for when you already know the output type.

See [When to Use Which](#when-to-use-which) before picking one.

---

## Monolithic Version (self-contained, no assembly)

Use this as a single drop-in prompt. It always includes a fidelity/nuance clause and a built-in generic structure fallback, so it degrades gracefully even when the session is messy, contradictory, or doesn't cleanly fit one category.

```
Process the entire available chat/session/workspace context as the single source of truth and produce a complete, coherent, production-quality output in clean Markdown — do not invent facts, steps, values, or claims that weren't actually present or confirmed in that context. Consolidate all relevant information, decisions, corrections, and refinements discussed so far into one unified piece, eliminating redundancy and repetition, resolving contradictions by treating the most recently confirmed version as authoritative, and explicitly flagging any gap you had to fill with a reasonable assumption. Preserve the original meaning, intent, and nuance of the source material rather than paraphrasing away important detail, adapt tone and register to suit the intended audience and purpose, and redact or placeholder any sensitive, private, or confidential information rather than reproducing it verbatim. Organize the output logically for its purpose — such as overview → context → details/body → examples → caveats/edge cases → references — keeping language concise, precise, and free of filler, while using clear headings, lists, tables, code blocks, or other Markdown elements only where they genuinely aid readability, to create a polished, self-contained, ready-to-use document that a reader unfamiliar with the original conversation could still fully understand.
```

### When and where to use the Monolithic version

**Use it when:**
- The session is **mixed, chaotic, or misguided** — contradictions, tangents, half-finished ideas, changed decisions mid-conversation
- You're **not sure in advance** what shape the output should take (workflow? summary? report? some blend?)
- You want a **fire-and-forget** prompt — no risk of forgetting to fill in a mode block or picking the wrong one
- It's a **one-off task** — not worth the overhead of assembling Core + Mode
- The output needs **both technical accuracy and human nuance/tone preserved** simultaneously (e.g. a session that mixes decisions, feelings, and specs)
- You're handing this prompt to someone else (a teammate, a template, an automation) who won't know how to correctly pick a mode

**Avoid it when:**
- You're running the **same well-defined task type repeatedly** (e.g. daily meeting digests) — the modular version is leaner and avoids unused clauses
- You need **tight control** over exactly which structural rules apply, without a generic fallback diluting the instruction
- Prompt length/token budget is a hard constraint and you know the exact mode needed

**Rule of thumb:** if you'd have to *think for more than a few seconds* about which Mode Block fits, the session is probably "mixed/misguided" enough that the Monolithic version is the safer default.

---

## Modular Version

### Core (always include)

```
Process the entire available chat/session/workspace context as the single source of truth and produce a complete, coherent, production-quality output in clean Markdown — do not invent facts, steps, values, or claims that weren't actually present or confirmed in that context. Consolidate all relevant information, decisions, corrections, and refinements discussed so far into one unified piece, eliminating redundancy and repetition, resolving contradictions by treating the most recently confirmed version as authoritative, and explicitly flagging any gap you had to fill with a reasonable assumption. Redact or placeholder any sensitive, private, or confidential information rather than reproducing it verbatim. [MODE BLOCK GOES HERE] Keep language concise, precise, and free of filler, using clear headings, lists, tables, code blocks, or other Markdown elements only where they genuinely aid readability, to create a polished, self-contained, ready-to-use document that a reader unfamiliar with the original conversation could still fully understand.
```

---

## Mode Blocks

### 1. Technical / Workflow
Use for: setup guides, dev docs, runbooks, config walkthroughs.

```
Preserve exact technical accuracy — commands, syntax, versions, and configurations must match what was actually established. Organize logically from overview → prerequisites → installation → configuration → usage → examples → troubleshooting → references, and use language-tagged code blocks throughout.
```

### 2. Summary / Digest
Use for: meeting notes, thread recaps, status updates.

```
Compress aggressively, surfacing only the decisions, conclusions, and action items that matter — omit exploratory back-and-forth. Organize as overview → key points → decisions made → open questions → next steps.
```

### 3. Creative / Narrative
Use for: stories, scripts, brand copy, narrative-driven writing.

```
Preserve the original meaning, tone, and nuance of the source material rather than paraphrasing away voice or intent; adapt register to suit the intended audience without flattening style. Organize with a natural narrative or thematic flow rather than a rigid technical structure.
```

### 4. Analytical / Report
Use for: research write-ups, evaluations, comparative analysis.

```
Preserve the original meaning and nuance of any claims, data, or reasoning rather than oversimplifying; where context includes conflicting evidence or interpretations, present both rather than silently picking one. Organize as overview → context → findings → analysis → caveats/limitations → references.
```

### 5. Instructional / How-To
Use for: tutorials, onboarding guides, step-by-step playbooks.

```
Ensure every step is actionable and sequential, with no skipped prerequisites; assume the reader has no access to the original conversation. Organize as overview → what you'll need → step-by-step instructions → expected outcome → common pitfalls.
```

---

## Assembly Examples

### Example A — Technical mode

```
Process the entire available chat/session/workspace context as the single source of truth and produce a complete, coherent, production-quality output in clean Markdown — do not invent facts, steps, values, or claims that weren't actually present or confirmed in that context. Consolidate all relevant information, decisions, corrections, and refinements discussed so far into one unified piece, eliminating redundancy and repetition, resolving contradictions by treating the most recently confirmed version as authoritative, and explicitly flagging any gap you had to fill with a reasonable assumption. Redact or placeholder any sensitive, private, or confidential information rather than reproducing it verbatim. Preserve exact technical accuracy — commands, syntax, versions, and configurations must match what was actually established. Organize logically from overview → prerequisites → installation → configuration → usage → examples → troubleshooting → references, and use language-tagged code blocks throughout. Keep language concise, precise, and free of filler, using clear headings, lists, tables, code blocks, or other Markdown elements only where they genuinely aid readability, to create a polished, self-contained, ready-to-use document that a reader unfamiliar with the original conversation could still fully understand.
```

### Example B — Summary mode

```
Process the entire available chat/session/workspace context as the single source of truth and produce a complete, coherent, production-quality output in clean Markdown — do not invent facts, steps, values, or claims that weren't actually present or confirmed in that context. Consolidate all relevant information, decisions, corrections, and refinements discussed so far into one unified piece, eliminating redundancy and repetition, resolving contradictions by treating the most recently confirmed version as authoritative, and explicitly flagging any gap you had to fill with a reasonable assumption. Redact or placeholder any sensitive, private, or confidential information rather than reproducing it verbatim. Compress aggressively, surfacing only the decisions, conclusions, and action items that matter — omit exploratory back-and-forth. Organize as overview → key points → decisions made → open questions → next steps. Keep language concise, precise, and free of filler, using clear headings, lists, tables, code blocks, or other Markdown elements only where they genuinely aid readability, to create a polished, self-contained, ready-to-use document that a reader unfamiliar with the original conversation could still fully understand.
```

---

## Notes on Design Choices

- **Anti-hallucination guardrail** — explicitly forbids inventing facts/steps not present in context.
- **Conflict resolution rule** — "most recently confirmed version wins" resolves contradictions deterministically.
- **Assumption flagging** — any gap filled by inference must be called out, not silently presented as fact.
- **Redaction clause** — sensitive/private/confidential data is placeholdered, not reproduced.
- **Audience-independence bar** — output must stand alone, understandable without the original conversation.
- **Purposeful formatting** — headings/tables/code blocks/emojis used only where they aid readability, never as decoration.

---

## How to Use

**Modular version:**
1. Copy the **Core** block.
2. Pick the **Mode Block** that matches your output type (or lightly blend two, e.g. Technical + Instructional).
3. Paste the mode block in place of `[MODE BLOCK GOES HERE]`.
4. Run it against your chat/session context.

**Monolithic version:**
1. Copy the single self-contained prompt as-is.
2. Run it directly — no assembly needed.

---

## When to Use Which

| Situation | Recommended |
|---|---|
| Session is messy, contradictory, or of uncertain shape | **Monolithic** |
| You already know the exact output type before running | **Modular** |
| One-off task | **Monolithic** |
| Repeated task of the same known type (e.g. daily digests) | **Modular** |
| Need both technical precision *and* nuance/tone preserved together | **Monolithic** |
| Want minimal, non-redundant instructions for a narrow use case | **Modular** |
| Handing the prompt to someone/something that won't self-diagnose the right mode | **Monolithic** |
| Token/length budget is tight and mode is certain | **Modular** |

**Note:** the Modular Core deliberately omits the fidelity/nuance clause and the generic structure fallback (they live only in Creative/Analytical mode blocks and are absent otherwise) to stay lean for known, well-defined tasks. This is a deliberate tradeoff, not an oversight — it's what makes the Modular version composable, but it's also why it's less resilient than the Monolithic version on unpredictable sessions.
