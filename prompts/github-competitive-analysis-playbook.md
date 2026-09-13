## Standardized method: repo structural extraction (use this for our own repo and every competitor repo)

Step 1 — Extract the full file tree via the Git Trees API:

GET /repos/{owner}/{repo}/git/trees/{branch_or_sha}

Add recursive=1 to include every nested object/subtree in one call. GitHub's docs confirm the recursive parameter is treated as "set" for any value passed — including the literal string "false" — so recursive=1 is the correct, unambiguous choice.

gh api \
  -H 'Accept: application/vnd.github+json' \
  -H 'X-GitHub-Api-Version: 2026-03-10' \
  'repos/{owner}/{repo}/git/trees/{branch}?recursive=1' \
  > {repo}.tree.json

Before trusting this as complete, check the "truncated" field in the response. GitHub caps the recursive tree at 100,000 entries or 7 MB — if truncated is true, paths are silently missing. If that happens, don't assume the tree is complete: fall back to the non-recursive form of this same endpoint and pull each subdirectory's tree individually until every path is accounted for.

Step 2 — Fetch the actual content of the files that matter; don't infer from filenames alone:

From the extracted tree, identify the highest-signal files — README*, CONTRIBUTING*, docs/**, package manifests (package.json, pyproject.toml, Cargo.toml, go.mod, etc.), CI/workflow configs, and top-level source entry points — and fetch their real content via the Git Blobs API (GET /repos/{owner}/{repo}/git/blobs/{file_sha}, using the sha each blob entry already has from Step 1) or the Contents API for convenience. Base every claim about a repo's purpose, stack, architecture, or maturity on this fetched content, never on filenames, folder names, or assumptions alone.

---

## Prompt 1 — Find competitors

Find this project's actual and genuine competitors from public repositories across all of GitHub.

## Prompt 2 — Establish our own baseline (also mine)

Before evaluating any competitor, run the standardized repo structural extraction method above against our own repository first, to get a complete and accurate map of what we actually have today — real file structure, real docs, real manifests, not assumptions — as the baseline everything else gets compared against.

## Prompt 3 — Triage candidates using ground-truth extraction, not chat-only summaries

For each candidate competitor repo found in Prompt 1, run the standardized repo structural extraction method above to get its actual file structure and real file contents, rather than relying solely on Copilot Chat's built-in repository-overview summary. Use this to filter out repos that are inactive, irrelevant, or too low-quality to be a genuine competitor, before committing to a full comparison.

## Prompt 4 — Compare against the competitors found

Compare against the <N> competitors found previously, using the structural data and fetched file content already extracted for our own repo and for each of theirs. Identify their weak areas, missing or notable features, and enhancements, and determine what we should adopt into our repo from each of them — grounded in what was actually found in their trees and files, not assumptions. The goal is to end up ahead of all <N> competitors.

## Prompt 5 — Multi-repo attached side-by-side comparison (Copilot Chat)

Attach our repository together with all <N> filtered competitor repositories in GitHub's built-in Copilot Chat (github.com/copilot), and ask for a single structured comparison across all of them at once — purpose, tech stack, architecture, contribution guidelines, and documentation quality — so we can compare and switch between them directly within one chat context instead of researching each repo in isolation. Cross-check anything Copilot summarizes here against the already-extracted tree/file data from Prompts 2–3 before accepting it as fact.

## Prompt 6 — Deep research mode for thorough competitive analysis

Using GitHub Copilot's deep research mode, run a research session grounded in the actual repository context of all <N> competitors to produce a comprehensive answer on the competitive landscape — covering adoption signals (stars, forks, contributor activity), architectural approach, and feature maturity — rather than a shallow, single-turn chat answer.

## Prompt 7 — Monitor active development via PR/diff context

For each of the <N> competitors, use Copilot Chat's diff/PR context ("Ask about this diff") on their most recently merged pull requests to identify what they're actively building or fixing right now, so our comparison reflects their current development direction, not just the static state of their default branch.

## Prompt 8 — Implementation-level deep-dive on identified weak areas

For each weak area already identified, use the repo's already-extracted file tree from the standardized method to locate the exact file or directory implementing that subsystem in each competitor's repository — rather than guessing the path — then ask Copilot Chat to explain how it's implemented there, so we get an implementation-level view of how competitors solved the same problem, not just a feature-level comparison.
