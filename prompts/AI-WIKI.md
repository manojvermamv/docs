
## Migrate this project from AGENTS.md DOX framework to obsidian-wiki

```
Migrate this project from AGENTS.md DOX framework to obsidian-wiki:

SETUP (one-time setup):
1. cd /your/project
2. pip install obsidian-wiki (Only if not installed)
3. obsidian-wiki setup --vault ./.brain --project .

MIGRATION:
1. Analyze the entire project structure: AGENTS.md, README, source code, git history, configuration files
2. Extract knowledge hierarchy from AGENTS.md and project docs (determine what's concept vs. reference vs. skill vs. entity)
3. Auto-map project knowledge to optimal wiki structure (concepts/, references/, entities/, skills/, synthesis/, journal/, projects/)
4. Convert all cross-references and documentation links to [[wikilinks]]
5. Generate wiki pages with proper frontmatter (title, category, tags, sources, created, updated)
6. Bootstrap project page from git history and README
7. Run: obsidian-wiki memory sync MIGRATE source="AGENTS.md" pages_created=N (where N is actual count)
8. Verify: obsidian-wiki doctor --project .

RESULT: Full wiki at ./.brain with complete project knowledge compiled, wikilinks connected, agent skills wired, ready for /wiki-update /wiki-query /wiki-capture
```


## Augment DOX Framework with obsidian-wiki (Dual Architecture: Discipline + Wisdom)

```
Augment DOX Framework with obsidian-wiki (Dual Architecture: Discipline + Wisdom):

LINKS:
- https://github.com/Ar9av/obsidian-wiki/blob/main/README.md
- https://github.com/agent0ai/dox/blob/main/README.md

CORE PHILOSOPHY:
- DOX Framework = DISCIPLINE: What agents MUST do (binding work contracts, operating rules, code ownership, verification gates in AGENTS.md). DOX is NOT replaced — it remains the binding execution contract.
- obsidian-wiki = WISDOM: What agents HAVE LEARNED (compounding memory, architectural patterns, lessons learned, concepts, synthesis in .brain/).
- Together: Every agent session operates with both discipline (DOX) and wisdom (wiki).

SETUP (one-time setup):
1. cd /your/project
2. pip install obsidian-wiki (Only if not installed)
3. obsidian-wiki setup --vault ./.brain --project .
4. Configure .env:
   OBSIDIAN_VAULT_PATH=./.brain
   OBSIDIAN_WIKI_REPO=.
   OBSIDIAN_LINK_FORMAT=wikilink
5. Initialize .brain/AGENTS.md for vault-specific conventions (taxonomy, frontmatter, link format).

KNOWLEDGE DISTILLATION & WIKI POPULATION:
1. Analyze the entire project: Root & Child AGENTS.md tree, README, source code, git history, configs.
2. Separate Contracts from Knowledge:
   - KEEP in AGENTS.md: Binding rules, file ownership, strict invariants, verification commands, closeout checklist.
   - EXTRACT to .brain/: Concepts, architectural patterns, entity profiles, factual references/specs, operational skills, and cross-cutting synthesis.
3. Auto-map distilled knowledge to optimal wiki structure:
   - concepts/     (patterns, architecture, mental models, state strategies)
   - entities/     (libraries, external APIs, companion tools, services)
   - skills/       (how-to guides, troubleshooting playbooks, operational knowledge)
   - references/   (specs, API contracts, schemas, RCA docs)
   - synthesis/    (cross-cutting trade-offs, system comparisons)
   - journal/      (milestone notes, migration logs)
   - projects/     (project identity, roadmap, stack overview)
4. Connect all cross-references across wiki pages using [[wikilinks]].
5. Generate pages with standard frontmatter: title, category, tags, sources, created, updated, summary.
6. Bootstrap project overview in .brain/projects/<project>.md from README and git history.
7. Compile master index (.brain/index.md), session hot cache (.brain/hot.md), and source manifest (.brain/.manifest.json).

DOX INTEGRATION & AGENT WIRING:
1. Retain master AGENTS.md and all child AGENTS.md contracts across the folder tree.
2. Update master AGENTS.md (and agent configs like CLAUDE.md / GEMINI.md) to define the dual architecture:
   - Section 1: DOX Framework (Binding Work Contracts & Child DOX Index)
   - Section 2: Obsidian Wiki (Vault Structure & Skill Routing)
   - Section 3: The Operational Loop (Discipline + Wisdom)
3. Wire agent skills for active maintenance:
   - /wiki-query   -> Read-only knowledge retrieval with [[wikilink]] citations
   - /wiki-update  -> Sync git deltas & architecture decisions into vault
   - /wiki-capture -> Record gotchas, bugs, and learnings into .brain/
   - /wiki-lint    -> Health check links, orphan pages, and taxonomy tags

OPERATING LOOP (Discipline + Wisdom in Action):
1. Before editing: Walk DOX chain for binding local rules; query .brain/ (or hot.md) for compiled wisdom.
2. While editing: Adhere strictly to DOX contracts and code ownership invariants.
3. After editing:
   - DOX Pass: Verify changes, run verification gates, update nearest AGENTS.md if contracts changed.
   - Wiki Pass: Capture new learnings or architectural shifts via /wiki-capture or /wiki-update.

VERIFICATION:
1. Verify DOX: Check all child AGENTS.md files are intact and active.
2. Verify Wiki: Run obsidian-wiki doctor --project . (or /wiki-lint).

RESULT: A unified project where DOX provides enforceable execution discipline and obsidian-wiki provides cumulative organizational memory.
```

