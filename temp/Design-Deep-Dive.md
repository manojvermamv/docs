# Coolify UI/UX Deep-Dive — Light & Dark Component Walkthrough

> Companion to `Design.md` (the concise citation index). This document is the exhaustive walkthrough:
> every component in **Light & Dark**, every mini/major UI helper, loader, offset-changer footer,
> terminal surface, and the "tweaks" override patterns. Class strings are quoted **verbatim** — never paraphrased.
>
> Source of truth: `resources/css/app.css` + `resources/css/utilities.css` (Tailwind v4 CSS-first,
> `@custom-variant dark` at `resources/css/app.css:15`) and `resources/views/components/*.blade.php`.
> Repo: `coolify`.

## Conventions used in this doc

- `!` after a utility = `!important` (e.g. `top-full!`). Tailwind v4 important modifier.
- `dark:` prefix = Dark-mode token swap. Every component is authored Light-first, Dark-second.
- Dark mode is class-based: `@custom-variant dark (&:where(.dark, .dark *));` (app.css **15**) — dark utilities activate under `<html class="dark">` (theme toggle swaps `document.documentElement.classList`), not a media query.
- Layer precedence: `app.css` is **unlayered** → its rules beat `@layer` utilities; component classes in `utilities.css` are emitted as unlayered `@utility`. When a Blade class bundle fights a CSS block, the `@utility` / unlayered rule wins on specificity ties — and a `!` suffix on a Blade utility always escapes.
- Color tokens (Graphite): semantic `fg`/`fg-dim`/`fg-faint` (#f2f2f2 / #b4b4b8 / #6e6e74), surfaces `panel`/`surface`/`raised`/`selected`, accent `--color-accent: #6b16ed` (coollabs purple), `--color-warning: #fcd452`, `--color-success: #22C55E`, `--color-error: #dc2626`, plus CSS vars `--coollabs-line` / `--coollabs-recessed` / `--coollabs-fill`. Dark fills are `white/[alpha]` (`dark:bg-white/[0.08]`), Light fills are `neutral-*` (`bg-neutral-100`). `color-mix()` blends for shadows/borders (see Part III).

---

# PART I — Component-by-Component (Light & Dark)

---

## A. FORMS

All form components live in `resources/views/components/forms/`; PHP resolvers in
`app/View/Components/Forms/`. Field surfaces are driven by the `input` / `select` / `button`
utilities in `utilities.css`, plus Alpine state for dirty-markers, toggles, and popovers.

### 1. Button (`components/forms/button.blade.php` + `Forms/Button.php`)

Resolver: `defaultClass = 'button'`; `noStyle` → `''`. **No variant classes anymore** — emphasis is a boolean flag: when `$isHighlighted` is true the blade emits a literal `isHighlighted` attribute on `<button>`, and CSS hooks it via the attribute selector `button[isHighlighted]:not(:disabled) { @apply button-highlighted; }` (app.css **291–293**). A sibling error hook exists: `button[isError]:not(:disabled) { @apply text-red-800 dark:text-red-300 bg-red-50 dark:bg-red-900/30 border-red-300 dark:border-red-800 hover:bg-red-300 hover:text-white dark:hover:bg-red-800 dark:hover:text-white; }` (app.css **287–289**).

Base `@utility button` (utilities.css **128–131**, verbatim):
```
@apply inline-flex shrink-0 gap-1.5 justify-center items-center whitespace-nowrap px-2.5 h-9 min-h-9 text-[13px] text-black normal-case rounded-md border outline-0 cursor-pointer font-medium transition-colors bg-white border-neutral-200 hover:bg-neutral-100 dark:bg-white/[0.06] dark:text-fg dark:hover:text-fg dark:hover:bg-white/[0.1] dark:border-white/[0.08] hover:text-black disabled:cursor-not-allowed min-w-fit dark:disabled:text-fg-faint disabled:border-neutral-200 dark:disabled:border-white/[0.06] disabled:hover:bg-transparent disabled:bg-transparent disabled:text-neutral-300 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent
```
Light = white bg / neutral-200 border / hover:bg-neutral-100; Dark = `white/[0.06]` bg ramp, `white/[0.1]` hover, `fg` text. Error styling comes from the `isError` attribute selector (red-50/red-300 family), not a class.

Gradient primary: `button-highlighted` (utilities.css **133–135**, verbatim):
```
@apply border-coollabs-200 bg-linear-to-b from-coollabs-100 to-coollabs-200 text-white! hover:from-coollabs-100 hover:to-coollabs hover:text-white!;
```
(Light = purple gradient `from-coollabs-100 to-coollabs-200`; Dark keeps the same gradient — not dark-flipped. Also forced onto `.application-heading-actions .button-highlighted` bundles, app.css **1801–1805**, with a custom-theme hover at app.css **997**.)

**Loading**: `wire:loading.class="is-loading"` + `wire:loading.attr="disabled"`; `.button.is-loading > svg:not(.animate-spin) { display: none; }` (utilities.css **151–153**) hides static label icons. A `x-loading-on-button` sub-component injects `<span class="inline-flex shrink-0 items-center gap-1.5"><svg class="size-3.5 shrink-0 animate-spin">…` in place of the label icon; the spinner uses `currentColor`, and `.dark .animate-spin { color: var(--color-warning) !important; }` (app.css **377–379**) flips it to warning-yellow. `wire:target` is derived in PHP from the `wire:click` value (or an explicit `wire:target`).

**Tooltip** (current, verified): wrapper is `relative inline-flex` with Alpine refs + `positionTooltip()` (not the old `group`-hover bubble); bubble class is the `auth-tooltip` utility (utilities.css **165–167**, `fixed z-[10000] px-2.5 py-1.5 text-xs ... pointer-events-none ...`); `$id('button-tooltip')` + `aria-describedby`, with `title` fallback.

---

### 2. Checkbox (`components/forms/checkbox.blade.php` + `Forms/Checkbox.php`)

Resolver default (verbatim):
```
peer absolute inset-0 z-10 m-0 h-full w-full cursor-pointer appearance-none opacity-0 disabled:cursor-not-allowed
```
The native input is an invisible **peer stretched over the box** (no `sr-only`), so the box flips purely via `peer-checked:`.

Row: `form-control group flex min-h-9 max-w-full items-center rounded-lg px-2.5 py-1.5 transition-colors` (+ `w-full` when `fullWidth`); hover `cursor-pointer hover:bg-neutral-100/80 dark:hover:bg-white/[0.035]`, `opacity-55` when disabled. Label = `label flex w-full max-w-full min-w-0 items-center gap-3 px-0`; text span `flex min-w-0 grow items-center gap-1.5 break-words text-[12px] text-neutral-600 dark:text-fg-dim`.

Box (verbatim — `pointer-events-none` overlay span, peer-stretched input underneath):
```
pointer-events-none absolute inset-0 rounded-[5px] border border-neutral-300 bg-white shadow-[inset_0_1px_1px_rgb(0_0_0/0.04)] transition-colors group-hover:border-neutral-400 peer-checked:border-coollabs peer-checked:bg-coollabs peer-focus-visible:ring-2 peer-focus-visible:ring-coollabs/25 peer-focus-visible:ring-offset-2 peer-disabled:opacity-50 dark:border-white/[0.14] dark:bg-white/[0.045] dark:shadow-none dark:group-hover:border-white/[0.22] dark:peer-checked:border-warning dark:peer-checked:bg-warning dark:peer-focus-visible:ring-warning/30 dark:peer-focus-visible:ring-offset-base
```
Check (verbatim — separate SVG, opacity-fade + scale, not text-tinted):
```
pointer-events-none absolute inset-0 m-auto size-3 scale-75 text-white opacity-0 transition-[opacity,transform] peer-checked:scale-100 peer-checked:opacity-100 dark:text-black
```
`@error` swaps helper to `text-red-500 label-text-alt`.

**Dark flip**: Light = purple box + white check; Dark = warning-yellow box + black check.

---

### 3. Collapsible (`components/forms/collapsible.blade.php`)

Alpine `open` state (no `wire:$toggle` anymore). Root: `flex flex-col gap-4`. Header is a `<button>`:
```
<button type="button" x-on:click="open = !open" class="flex items-center gap-2 text-left text-sm font-medium hover:underline" :aria-expanded="open">
  <svg chevron class="size-4 transition-transform" x-bind:class="open && 'rotate-90'">
```
Panel (verbatim):
```
<div x-show="open" x-cloak class="rounded-lg border border-neutral-200 p-4 dark:border-coolgray-400 {{ $contentClass }}">
```

---

### 4. Copy Button (`components/forms/copy-button.blade.php`)

Read-only input + overlay copy button. Input (verbatim):
```
class="input input-with-copy-button bg-white dark:bg-coolgray-100 dark:read-only:bg-coolgray-100 dark:read-only:text-white"
```
Button (verbatim):
```
copy-button flex absolute inset-y-0 right-0 z-10 items-center pr-2 cursor-pointer text-neutral-500 transition-colors hover:text-black focus-visible:ring-2 focus-visible:ring-coollabs focus-visible:ring-offset-2 dark:text-neutral-400 dark:hover:text-white dark:focus-visible:ring-warning dark:focus-visible:ring-offset-base
```
`copied` Alpine state swaps the icon (`size-[18px]`, check colored `text-green-500`) for **1s** (`setTimeout(..., 1000)`) after `await window.copyToClipboard(...)`. Input blocks editing (`@keydown.prevent @paste.prevent @cut.prevent @drop.prevent`) and auto-selects on focus (`@focus="$event.target.select()"`). Label: `flex gap-1 items-center mb-1 text-sm font-medium text-black dark:text-white`.

---

### 5. Datalist (`components/forms/datalist.blade.php`)

Multi-chip mode — options area (verbatim):
```
class="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto scrollbar py-1.5 px-2 w-full text-sm rounded-sm border-0 bg-white dark:bg-coolgray-100 ...
```
Chips: `<span class="chip">` + `<button type="button" class="chip-remove">` (app.css `chip-input`/`.chip`/`.chip-remove` block); remove icon `size-3`. Selected option rows are `listbox-option` with an inline `:style` focus rail; whole control gets `wire:loading.class="opacity-50"`. Label: `flex gap-1 items-center mb-1 text-sm font-medium` + `text-neutral-600` when `$disabled`.

---

### 6. Domain Chips (`components/forms/domain-chips.blade.php`)

Token input (typing + Enter/`,` commits, Backspace on empty removes). Label: `mb-1 flex w-fit items-center gap-1.5 text-sm font-medium`. Chip markup (verbatim):
```
<div class="chip-input" x-data="{ ... }">
  <span class="chip">...</span>
  <button type="button" class="chip-remove" x-show="canUpdate">  <- × (size-3 svg)
```
Styling in app.css `chip-input` block; chip pills + remove button tuned for both themes.

---

### 7. Domain Input (`components/forms/domain-input.blade.php`)

Subdomain / host / TLD split grid (verbatim):
```
<div class="grid gap-4 sm:grid-cols-[8rem_minmax(0,1fr)_8rem]">
```
Each cell `min-w-0`; scheme cell is an `x-forms.listbox` (Protocol, `portal`), host + TLD are plain `input`s; labels `mb-0! flex items-center gap-1.5 leading-4` (row `mb-1.5 flex h-4 w-full items-center gap-1.5`).

---

### 8. Env Var Input (`components/forms/env-var-input.blade.php`)

Label row `mb-1.5 flex h-4 w-full items-center gap-1.5`; label `mb-0! flex items-center gap-1 text-sm font-medium leading-4`. Value field dirty state (verbatim — shared across all text inputs):
```
wire:dirty.class="[box-shadow:inset_4px_0_0_#6b16ed,inset_0_0_0_2px_#e5e5e5] dark:[box-shadow:inset_4px_0_0_#fcd452,inset_0_0_0_2px_#242424]"
```
(Light = 4px purple left rail; Dark = warning-yellow rail.) Type badge pills (`text/secret/multiline`) + `@success.window="type = '{{ $type }}'"`; value cell uses the same `password-toggle` as Input (below). Truncation on the value when `type === 'text' && ! $el.disabled` (`x-bind:class`).

---

### 9. Input (`components/forms/input.blade.php` + `Forms/Input.php`)

Resolver: `defaultClass = 'input'`; password fields append `input-with-password-toggle`.

Shared visual base — `@utility input-select` (utilities.css **61–76**, verbatim; also used by `select`):
```
@apply block h-9 px-3 py-1.5 w-full text-sm text-black rounded-md border border-neutral-200 bg-white dark:bg-surface dark:text-fg dark:border-white/[0.08] transition-colors disabled:bg-neutral-100 disabled:text-neutral-400 dark:disabled:bg-white/[0.03] dark:disabled:text-fg-faint
```
`@utility input` (utilities.css **79–101**) composes it, adding read-only + placeholder overrides (verbatim):
```
@apply dark:read-only:text-neutral-500 dark:read-only:bg-coolgray-100/40 placeholder:text-neutral-300 dark:placeholder:text-neutral-700 read-only:text-neutral-500 read-only:bg-neutral-200;
@apply input-select;
@apply focus-visible:outline-none;
```
Focus: inside the utility body — `&:focus-visible { border-color: var(--color-accent); box-shadow: 0 0 0 1px var(--color-accent); }` (same accent in Light & Dark; `--color-accent: #6b16ed`). The old ring-based `input-focus` utility (utilities.css **56–58**, `focus-visible:ring-2 focus-visible:ring-coollabs dark:focus-visible:ring-warning ...`) still exists but is **not referenced by current form blades** — `input`/`select` implement their own `&:focus-visible`.

Dirty state (verbatim — same bundle as env-var-input):
```
wire:dirty.class="[box-shadow:inset_4px_0_0_#6b16ed,inset_0_0_0_2px_#e5e5e5] dark:[box-shadow:inset_4px_0_0_#fcd452,inset_0_0_0_2px_#242424]"
```
Label row: `mb-0! flex items-center gap-1 text-sm font-medium leading-4`; helper kept **outside** the `<label>` (so taps don't steal focus); required mark = `x-highlighted text="*"`; `@error` swaps helper to `text-red-500 label-text-alt`.

**Password toggle** (`input-with-password-toggle` + `password-toggle`):
```
password-toggle flex absolute inset-y-0 right-0 z-10 items-center pr-2 cursor-pointer text-neutral-500 hover:text-black dark:text-neutral-400 dark:hover:text-white
```
toggles `type=text/password`; eye icons are reicon `eye`/`eye-off2` at `size-[18px]`.

**Mobile text-size rule**: app.css **247–253** — `@media (max-width: 767px) { :root input, :root textarea, :root select { font-size: 16px !important; } }` (prevents iOS zoom).

---

### 10. Listbox (`components/forms/listbox.blade.php`)

Headless-style trigger/panel/option trio, styled in app.css **~1872–1993**:
- `.listbox-trigger`: `height: 2.25rem; border: 1px solid var(--coollabs-line); background: var(--coollabs-recessed); font-size: 0.875rem; color: #000000` (dark: `color: var(--color-fg)`).
- `.listbox-panel` (verbatim): `position: absolute; top: calc(100% + 0.25rem); left: 0; z-index: 30; min-width: max(100%, 13rem); max-width: min(24rem, calc(100vw - 1.5rem)); max-height: 16rem; border-radius: 10px; background: var(--coollabs-recessed); box-shadow: 0 12px 32px rgba(0,0,0,0.45)` — **absolute, not portaled** by default (z-30, not the old z-50); a mobile variant drops max-width.
- `.listbox-option`: min-height 2rem, padding, radius 6px, `color: #000000` / dark `var(--color-fg)`, hover `background: var(--coollabs-fill)`; `.listbox-option-disabled` for inert rows.

Label row: `mb-0! flex items-center gap-1.5 leading-4`; helper outside the label ("Keep helper outside the label so taps do not open the listbox trigger").

---

### 11. Monaco Editor (`components/forms/monaco-editor.blade.php`)

- Wrapper: `coolify-monaco-editor flex-1`; inner `relative z-10 w-full h-full`.
- Editor element: `w-full text-md {{ $readonly ? 'opacity-65' : '' }}`, height from `--editor-height` CSS var (default `calc(100vh - ...)`).
- Line-number ghost (verbatim): `w-full text-sm font-mono absolute z-50 text-gray-500 ml-14 -translate-x-0.5 mt-0.5 left-0 top-0`.
- Custom theme `coolify-dark` registered via `monaco.editor.defineTheme`; `wire:model` syncs via `onDidChangeModelContent` → `$wire.set()` (debounced).

---

### 12. Searchable Listbox (`components/forms/searchable-listbox.blade.php`)

Listbox + free-text filter. Same label row + `relative min-w-0` wrapper as listbox; `x-modelable="value"`; saving state `:class="{ 'pointer-events-none opacity-70': saving }"`. Typing filters options in-memory; empty state renders a muted message; Enter selects first filtered match.

---

### 13. Select (`components/forms/select.blade.php` + `Forms/Select.php`)

Resolver: `defaultClass = 'select w-full'`.

`@utility select` (utilities.css **103–126**) — composes the shared `input-select` base + a data-URI chevron (verbatim core):
```
@apply w-full;
@apply input-select;
@apply focus-visible:outline-none;
background-image: url("data:image/svg+xml,… black chevron …");
background-position: right 0.5rem center;
background-repeat: no-repeat;
background-size: 1rem 1rem;
padding-right: 2.5rem;
```
- Chevron drawn via **data-URI background-image** (black in Light / white in Dark through `&:where(.dark, .dark *)`) — no svg element.
- Focus ring identical to `input`: `&:focus-visible { border-color: var(--color-accent); box-shadow: 0 0 0 1px var(--color-accent); }`.
- Dirty state: same `[box-shadow:inset_4px_0_0_#6b16ed...]` bundle as Input.
- Error: `text-red-500 label-text-alt`. Option rows styled in app.css **283–285** (`option { @apply dark:text-white dark:bg-coolgray-100; }` — needed since `<option>` ignores CSS otherwise).

---

### 14. Textarea (`components/forms/textarea.blade.php` + `Forms/Textarea.php`)

Resolver: `defaultClass = 'input scrollbar'`; `defaultClassInput = 'input'`; monospace mode appends `font-mono`.
- `textarea.input`: `rows` prop, min-height, same border/ring family as `input`.
- **Tab key inserts 2 spaces** (`@keydown.tab.prevent` JS), no focus loss.
- Optional delegation: when `$monaco` is true, renders the Monaco component instead (config/ENV editing path).

**Form control wrapper**: `label` = `text-sm font-medium`, `text-helper` underneath, `@error` swaps helper to `text-red-500 label-text-alt`.

---

## B. OVERLAYS

### Z-Ladder (authoritative, low→high — verified against current source)

| z | Surface |
|---|---|
| `z-10` | in-field overlays (password toggle, copy button) |
| `z-30` | `.listbox-panel` base (CSS) — absolute, not portaled |
| `z-50` | page-loading overlay; mobile bottom bar |
| `z-[90]!` | all listbox/table dropdown panels that escape containers: table dropdown, status-summary, breadcrumb-switcher, resource-heading-overflow |
| `z-[1000]` | resource-actions-open lift (`:class="{ 'z-[1000]': resourceActionsOpen }"` on app shell); unsaved-bar |
| `z-9999` | toast stack (global, above everything transient) |
| `z-[10000]` | tooltip bubbles (`info-helper-popup`, `auth-tooltip`) |
| `z-[100000]` | terminal fullscreen shell (`terminal-fullscreen-shell`) |

Notes: panels are positioned **absolute** in their relative wrapper (not portaled); blades that must escape `overflow-hidden` parents add the `!` suffix + `z-[90]!` (e.g. `listbox-panel fixed! top-auto! right-auto! bottom-auto! z-[90]! mt-0!` on table dropdown). Terminal fullscreen is the single highest surface. The `z-[60]!` escape from earlier versions is gone.

### Backdrop / Close matrix (verified current)

| Dialog | Backdrop closes? | Close affordance |
|---|---|---|
| `modal-confirmation` | **Never** (confirmation = explicit decision) | buttons only |
| `modal-input` | via `@click.self` (`$closeOutside`) | X, buttons, Esc |
| `modal` | `@click.self` | X, buttons |
| `process-dialog` | **no backdrop close** | X only (`$closeWithX`) |
| `slide-over` | via `$closeWithX` | X, Esc |
| `toast` | — | auto-dismiss, hover-pause, X |
| `banner` / `popup` | `@click.self` | X |

**ARIA status**: `modal-confirmation` / `modal-input` / `process-dialog` carry `role="dialog"` + `aria-modal="true"` + `aria-labelledby` wired to title ids, focus moved into panel on open (`x-trap`/JS). `slide-over` lacks a focus trap (known gap — Esc works, Tab can escape).

### Motion (Light & Dark identical)

| Surface | Enter | Leave | ms |
|---|---|---|---|
| modal-confirmation / modal-input | `opacity-0 -translate-y-2 sm:scale-95` → in | fade + down | 200 / 150 |
| process-dialog | `opacity-0 translate-y-2` → up (slides **up** from bottom) | fade down | 100 / 100 |
| slide-over (right) | `translate-x-full` → 0 | → `translate-x-full` | 300 / 200 |
| toast | `opacity-0 translate-y-2` scale | fade | 200 / 150 |

All transitions are `transition` (CSS) driven by Alpine `x-show` + `x-transition`, never keyframes.

### Component notes (verified current)

- **modal** (`components/modal.blade.php`): panel `rounded-sm modal-box max-h-[calc(100vh-5rem)] flex flex-col` (`wire:submit` form); trigger lifts `z-40` while open; overlay `fixed inset-0 z-99 overflow-y-auto`; backdrop `absolute inset-0 w-full h-full bg-black/50 backdrop-blur-[2px]`.
- **modal-input**: `fixed inset-0 z-99 overflow-y-auto`, backdrop `bg-black/50 backdrop-blur-[2px]`, `x-transition:enter-start="opacity-0 -translate-y-2 sm:scale-95"`, `@click.self` close via `$closeOutside`, Esc via `@keydown.window.escape`.
- **modal-confirmation**: `fixed inset-0 z-99 flex min-h-full items-center justify-center overflow-y-auto p-4`, backdrop `bg-black/50 backdrop-blur-[2px]`, `@keydown.escape.window` resets state (`resetModal()`).
- **process-dialog** (`components/process-dialog.blade.php`): `relative z-99`; backdrop `bg-black/50 backdrop-blur-[2px] dark:bg-black/60`; panel sizes (verbatim): `md` → `min-w-0 w-full max-w-2xl sm:min-w-[28rem]`, `xl` → `min-w-0 w-full max-w-5xl sm:min-w-[36rem] lg:min-w-[48rem]`, default → `min-w-0 w-full max-w-4xl sm:min-w-[32rem] lg:min-w-[42rem]`.
- **slide-over** (`components/slide-over.blade.php`): `relative z-99`, right-side drawer `fixed inset-y-0 right-0 flex max-w-full pl-10`, `translate-x-full` default, backdrop `fixed inset-0 dark:bg-black/60 backdrop-blur-xs`.
- **toast** (`components/toast.blade.php`): `window.toast()` JS API (title, message, type, duration); wrapper `fixed z-9999 flex w-[calc(100%-2rem)] gap-2.5 sm:max-w-[26rem]` + position classes (`right-4`/`left-4`/`left-1/2 -translate-x-1/2`/`top-4`/`bottom-4`, `flex-col` vs `flex-col-reverse`); item `relative flex w-full items-start rounded-lg` with `p-3.5 pr-20` (or `p-0` for `toast.html`); stack **max 4** (oldest evicted); **hover pauses** auto-dismiss; icon per type: check/error/info tinted.
- **banner** (`components/banner.blade.php`): `z-999`, `bg-coolgray-100`, `x-transition` slide-down/up (`-translate-y-10` ↔ 0).
- **popup** (`components/popup.blade.php`): `z-999`, `fixed bottom-0 right-0 w-full`, slides up from bottom (`translate-y-full` ↔ 0), `@click.self` close.
- **unsaved-bar** (`components/unsaved-bar.blade.php`): `pointer-events-none fixed inset-x-3 bottom-[calc(var(--keyboard-inset,0px)+max(1.5rem,env(safe-area-inset-bottom,0px)+0.75rem))] z-[1000]`, appears when any `wire:dirty` target is dirty; Save button = `danger` variant.
- **loading** (`components/loading.blade.php`): inline arc spinner + optional text (see Part II — Loaders).
- **page-loading** (`components/page-loading.blade.php`): full overlay + centered spinner; `wire:loading` global flicker mask on Livewire navigation.
- **empty** (`components/empty.blade.php`): empty-state block; helper text (verbatim): `mt-1 max-w-sm text-[12px] leading-5 text-neutral-500 dark:text-fg-dim` (default `text-[13px]`), optional CTA slot.
- **checkpoint-item / upgrade-progress**: list-row renderers inside upgrade flows; `upgrade-progress` = step stepper with completed checkmarks (emerald) and current pulse.

---

## C. LAYOUT & NAVIGATION

### App shell (`resources/views/layouts/app.blade.php`) — verified current

```
<body class="dark:text-inherit text-black">
  ┌ layer 1: top bar  (hidden lg:flex fixed top-0 inset-x-0 z-50 h-12 items-center bg-white/95 dark:bg-panel/95 backdrop-blur)
  │            sidebar rail inside: border-r border-neutral-200 dark:border-white/[0.06] transition-[width] duration-200
  │            :class="collapsed ? 'w-16 justify-center px-0' : 'w-56 px-4'"
  └ layer 2: content column <div class="flex flex-col"> (header + main)
```
- **Sidebar collapse** persisted (Alpine `localStorage`): `w-16` (icons only) ↔ `w-56`; `transition-[width] duration-200`. Logo `size-5`, product name `text-[15px] font-semibold tracking-tight text-black dark:text-white` (x-show when expanded), version chip `!text-[10.5px] font-medium text-neutral-400 dark:text-fg-faint !opacity-100 hover:!opacity-100 dark:hover:text-fg hover:text-black`.
- Theme toggle swaps `document.documentElement.classList.toggle('dark')` + localStorage.

### Sidebar (`components/dashboard/sidebar.blade.php`) + header strip (`components/dashboard/navbar.blade.php`)

- Nav items: `flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs`; **active state** (verbatim):
```
bg-coollabs/10 text-coollabs shadow-sm ring-1 ring-coollabs/25 hover:bg-coollabs/15
dark:bg-warning/15 dark:text-warning dark:ring-warning/25 dark:hover:bg-warning/20
```
inactive: `text-neutral-500 dark:text-fg-dim hover:bg-neutral-100 dark:hover:bg-white/[0.06] hover:text-black dark:hover:text-fg`.
- Group labels: `text-[10px] uppercase tracking-widest text-neutral-400 dark:text-fg-faint`.
- **Header strip**: `w-full lg:fixed lg:top-12 lg:right-0 lg:z-30 lg:h-12 lg:w-auto lg:border-b lg:border-neutral-200 lg:bg-white/95 lg:pr-4 lg:pl-2 lg:backdrop-blur lg:transition-[left]` — floats under the top bar on desktop, inline on mobile. Page title `min-w-0 truncate text-[24px]! leading-7! font-semibold! tracking-tight!`. Breadcrumb pill row (verbatim): `flex min-w-0 w-full items-center gap-0.5 overflow-x-auto rounded-[10px] border border-neutral-200 bg-neutral-100 p-1 sm:flex-1 dark:border-white/[0.07] dark:bg-white/[0.06]`, active pill = coollabs/warning tint (same bundle as nav active).

### User menu

Avatar `h-8 w-8 rounded-full` (initials circle or uploaded image) → dropdown panel (listbox style, `z-[90]!` escape): name+email header, links, divider, Logout. `@click.self` backdrop close.

### Settings layouts (`components/settings/*`)

`settings-layout` (team-scoped), `settings/layout`, `server/settings-layout`: sidebar-of-sections + content column `flex-1 min-w-0`; section items reuse the sidebar item classes. Breadcrumb row: `top-breadcrumb` + `breadcrumb-switcher` — panel (verbatim): `listbox-panel scrollbar left-0! z-[90]! max-h-80! min-w-56 max-w-72`.

### Auth & Error shells

- `layouts/simple.blade.php`: centered single-column card on `min-h-screen`; card `w-full max-w-md ... rounded-xl`.
- `layouts/error.blade.php`: full-screen centered, big status code, message, "Back to Dashboard" (button inverse).
- `layouts/boarding.blade.php`: step shell with `boarding-progress`/`boarding-step`: step dots/line (`flex items-center`), active = scaled accent dot, done = checkmark, pending = neutral.

### Magic bar (`components/magic-bar.blade.php`)

Floating command palette trigger — circular button; opens a full palette (`searchable-listbox` behavior, commands grouped, kbd hints).

---

## D. DATA DISPLAY

### Tables (`components/table.blade.php`)

- Wrapper: `data-table` (app.css ~**1980–2140**); header grid `.data-table-header` (app.css **2117**, verbatim):
```
display: grid; align-items: center; gap: 1rem; padding: 0 1rem; height: 2.5rem;
font-size: 13px; font-weight: 500; color: var(--coollabs-subtle); background: rgba(0, 0, 0, 0.02);
```
dark: `background: rgba(255, 255, 255, 0.02)` (`.dark .data-table-header`, app.css **2131**).
- **Active row** (`.data-table-row-active`, app.css **1983**, verbatim):
```
background: var(--coollabs-fill);
color: var(--coollabs-fg);
```
- Cell padding `px-3 py-2.5 text-xs`; right-aligned numeric columns use `tabular-nums`. Env-table rows: `.data-table > .env-table-item` (app.css **2135**).

### Toolbar / search / filter / sort / loading — verified current

Components split into `components/table/{toolbar,search,filter,sort,loading,dropdown}.blade.php`.

- **Toolbar** (`table/toolbar.blade.php`): two flex children — search slot `min-w-0 w-full flex-1 sm:max-w-md` and actions `flex flex-wrap items-center gap-2 sm:ml-auto`.
- **Search** (`table/search.blade.php`): wrapper `table-search relative min-w-0 w-full`; leading reicon (`<x-reicon name="search" class="size-3.5 text-neutral-400 dark:text-fg-faint" ...>`) with `wire:loading.remove wire:target`, swapped to an arc-spinner svg (`wire:loading wire:target`) while searching.
- **Filter** (`table/filter.blade.php`): `table-filter` wrapper; trigger is a `button` with `@class(['button max-w-80 min-w-0', 'button-highlighted' => $activeCount > 0])` + `<x-reicon name="filter" class="size-3.5 shrink-0" />`; panel via `x-table.dropdown panel-class="w-44! overflow-hidden! p-0!" :multiselectable="true"` (multi-select chips inside).
- **Sort** (`table/sort.blade.php`): `table-sort` wrapper; `<button type="button" class="button">` + `<x-reicon name="sort-direction" class="size-3.5" />`; panel `x-table.dropdown panel-class="w-44!"`.
- **Loading** (`table/loading.blade.php`): `<div wire:loading.flex wire:target="{{ $target }}">` wrapping `<x-loading aria-label="{{ $text }}" class="[&_.loading-indicator]:size-5" />`.
- **Dropdown** (`table/dropdown.blade.php`): per-row action menu — Alpine `panelStyle` computes **inline `position: fixed`** (viewport-clamped, flips above when tight); panel class (verbatim):
```
listbox-panel fixed! top-auto! right-auto! bottom-auto! z-[90]! mt-0!
```
plus caller `panel-class` (e.g. `min-w-24!`, `w-44!`). This replaces the old portaled `z-50` approach.

### Pagination footer (`components/table-pagination.blade.php`)

`<footer>` (verbatim):
```
flex min-h-11 items-center justify-between border-t border-neutral-200 px-4 text-[11px] text-neutral-500 dark:border-white/[0.08] dark:text-fg-faint
```
Summary (verbatim, en-dash `–`, `tabular-nums`):
```
<span class="inline-flex h-7 items-center whitespace-nowrap tabular-nums">{{ $from }}–{{ $to }} of {{ $total }}</span>
```
Prev/Next buttons share one `$buttonClass` (verbatim):
```
flex size-7 items-center justify-center rounded-md border border-neutral-200 text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-black disabled:pointer-events-none disabled:opacity-35 dark:border-white/[0.08] dark:text-fg-dim dark:hover:bg-white/[0.06] dark:hover:text-fg
```
- `size-7` (28px) square buttons; prev icon is `arrow-right` rotated 180° (`<x-reicon name="arrow-right" class="size-3.5 rotate-180" />`), next is plain.
- `aria-label="Previous page"` / `"Next page"`, `@disabled` on first/last page.
- Loading (when `wireTarget` set):
```
<span wire:loading.inline-flex wire:target="..." class="inline-flex items-center" aria-live="polite">
  <svg class="loading-indicator size-3.5 animate-spin" ...>  <- arc spinner (opacity-25 circle + opacity-75 path)
  <span class="sr-only">Loading page…</span>
```
- `$pageSize` slot renders `page-size-select` inside the footer; footer hides entirely when `$total === 0`.

`page-size-select` (`components/page-size-select.blade.php`) — the offset-changer: Alpine machine with `localStorage` persistence, clamp `1–100`, options [10, 25, 50, 100] + **Custom…** row that swaps panel to a numeric input (`@keydown.enter`/`@keydown.escape`/`@blur` commit, `min="1" max="100" inputmode="numeric"`). Trigger (verbatim):
```
inline-flex h-7! w-12! items-center justify-between border-0 px-1 text-[11px]! leading-none! tabular-nums text-neutral-500 transition-colors hover:text-black dark:text-fg-dim dark:hover:text-fg
```
Custom input (verbatim):
```
mb-0! h-7! w-14! rounded-md! border-neutral-200! bg-transparent! px-1.5! py-0! text-[11px]! tabular-nums shadow-none! focus:border-neutral-300! focus:ring-0! dark:border-white/[0.08]! dark:text-fg-dim!
```
Options render as `listbox-option` rows with `check` reicon on the selected one; the panel is `x-table.dropdown panel-class="min-w-24!"`. `$livewire` mode calls `$wire.set(model, value)`, non-Livewire mode sets the Alpine binding + `page = 1`. Client-side variant (`client-pagination.blade.php`) filters an Alpine array instead.

### Status badges (`components/status-badge.blade.php` + `components/status/*`)

Base pill (`$baseClasses`, verbatim):
```
inline-flex h-6 max-w-full items-center gap-1.5 whitespace-nowrap rounded-full border border-neutral-200 bg-neutral-100 px-2 text-xs font-medium leading-none text-neutral-700 dark:border-white/[0.12] dark:bg-white/[0.07] dark:text-white
```
Dot (`size-1.5 shrink-0 rounded-full`) + label (`truncate`). `as` prop: `span` (default), `button` (adds `transition-colors`, used by status-summary's popover trigger), `a`. `dynamic` = slot overrides the auto dot+label.

Type → dot map (verbatim):
```
neutral: bg-neutral-400 dark:bg-neutral-500
success: bg-emerald-500
warning: bg-warning        <- theme token (--color-warning: #fcd452)
error:   bg-red-500
```

Variant files (`components/status/`) — each maps a raw Docker status to a badge:

| Status | type | Notes |
|---|---|---|
| running | `success` | emerald dot |
| restarting | `warning` | amber/warning dot |
| degraded | `warning` + `dynamic` custom label | container state exists but unhealthy |
| stopped | `neutral` | gray dot |
| services | `neutral` w/ count | "N services" label |
| index | `neutral` | dispatcher used by list rows |

- `status-summary.blade.php` (current, verified): **popover dropdown**, not a static row. Trigger = `x-status-badge as="button" dynamic` with rotating chevron (`<x-reicon name="chevron-down" class="size-3 opacity-55" />` in `inline-flex transition-transform` `:class="open && 'rotate-180'"`); panel (verbatim):
```
listbox-panel top-8! right-auto! left-0! z-[90]! w-[min(16rem,calc(100vw-1.5rem))]! min-w-0! sm:w-64! sm:min-w-64!
```
Panel body: title `px-3 py-2 text-[11px] font-medium text-neutral-400 dark:text-fg-faint`, then two `listbox-option cursor-default! gap-2.5!` rows (container state + healthcheck), each with its own `size-1.5 shrink-0 rounded-full bg-success/bg-warning/bg-error` dot. Status strings parsed from Docker `running/starting/...` + health `(healthy|unhealthy|starting)`; `x-transition.origin.top.left` enter. `@click.outside` + `@keydown.escape.window` close. `z-[90]!` — same escape as table dropdowns.
- `server/status-summary`: same pattern for servers.
- `deprecated-badge`: `bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400` + strikethrough on the resource name.
- `two-factor-badge`: emerald "2FA Enabled" pill next to user rows.

### Resource heading tabs (`components/resource-heading-tabs.blade.php`)

Tab pills reuse the `app-tab` / `app-tab-active` utilities (utilities.css **156–163**):
```
@utility app-tab { @apply inline-flex items-center gap-1 h-7 px-2.5 rounded-md text-[13px] font-medium text-neutral-500 dark:text-fg-dim hover:bg-neutral-100 dark:hover:bg-white/[0.05] hover:text-black dark:hover:text-fg transition-colors; }
@utility app-tab-active { @apply bg-coollabs/10 text-coollabs shadow-sm ring-1 ring-coollabs/25 hover:bg-coollabs/15 dark:bg-warning/15 dark:text-warning dark:ring-warning/25 dark:hover:bg-warning/20; }
```
Active = coollabs/warning tint pill with `aria-current="page"`; disabled tabs get `opacity-40 cursor-not-allowed`. Overflow: `resource-heading-overflow` (`is-collapsed` JS) renders a "More" dropdown; trigger `button resource-heading-overflow-trigger` (`aria-haspopup="menu"`), panel (verbatim):
```
listbox-panel top-full! right-0! left-auto! mt-1! min-w-52!
```

### Resource view card (`components/resource-view.blade.php`)

`data-table`-family card: header `px-4 py-3 border-b` with title + description + right-slot actions; body with `wire:key` guards for Livewire re-renders.

### Links — verified current (icons, not text links)

- `external-link` (`components/external-link.blade.php`): **an SVG icon** (arrow-up-right), not a text link. Default class (verbatim): `inline-flex w-3 h-3 dark:text-neutral-400 text-black`.
- `internal-link` (`components/internal-link.blade.php`): **an SVG icon** (left-right arrow). Default class (verbatim): `inline-flex w-4 h-4 text-black dark:text-white`.
- `auth-text-link` and `error-contact-link` component files **no longer exist** — text links are plain `<a>` with text utilities (e.g. `text-accent hover:underline`).

# PART II — Mini UI-UX Helper Atlas

## E. ICON SYSTEM (`components/reicon.blade.php` — the reicon catalog)

**Data-driven Blade component** — one file holds a PHP `$icons` map (`name => inner SVG markup`), rendered through a shared wrapper. Usage: `<x-reicon name="chevron-down" class="size-3" />`. Wrapper (verbatim):
```blade
@props(['name'])
@php $svg = $icons[$name] ?? ''; @endphp
<svg {{ $attributes->merge(['class' => 'size-4']) }} viewBox="0 0 24 24" fill="none"
    xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    {!! $svg !!}
</svg>
```
- Default class `size-4` (16px); every icon is sized via the `class` attribute (`size-3`, `size-3.5`, `size-5`, …) — no size props.
- All glyphs use `currentColor` (converted from the reicon pack's `#000000`), so tinting = any `text-*` utility on the element (or `text-current` from a parent button).
- **Two glyph styles coexist in the map**: fill-based paths (`fill="currentColor"`, with `fill-rule="evenodd" clip-rule="evenodd"` for complex shapes) and stroke-based paths (`stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"`). The `viewBox="0 0 24 24" fill="none"` wrapper means stroke icons render as strokes; fill icons paint their fill.
- A few legacy Phosphor-derived icons (`broom`, `shield-star`, `network`) carry an inline `transform="scale(0.09375)"` — 256-unit path data scaled into the 24-unit viewBox.
- Missing name → renders empty `<svg>` (safe fallback, no exception).

**Full catalog — 69 icons** (verbatim keys):

| Family | Icons |
|---|---|
| Nav / shell | dashboard, projects, servers, sources, destinations, storages, variables, notifications, keys, tags, profile, teams, subscription, settings, admin, sponsor, documentation, feedback, logout, terminal, browser-terminal |
| Status | alert-triangle, alert-circle, check-circle, info-circle, shield-alert, shield-star, stop, stop-circle, play-circle, restart |
| Actions | search, plus, x, check, chevron-down, arrow-right, trash, upload, external-link, refresh, refresh3, sort-direction, filter, sliders, eye, eye-off, eye-off2, grid, file, file-content, folder, unordered-list, browser-code, server-update, calendar, time-back, cpu, graph, network, bandage, broom, globe, cloud, database, layers |
| Brand/symbols | fire, code, mail |

Verified usage examples (verbatim):
```blade
<x-reicon name="chevron-down" class="size-3 opacity-55" />                                  <- popover trigger, rotate-180 when open
<x-reicon name="chevron-down" class="size-3 text-neutral-400 dark:text-fg-faint" />         <- page-size trigger
<x-reicon name="arrow-right" class="size-3.5 rotate-180" />                                 <- pagination "Previous" (rotated arrow)
<x-reicon name="check" class="size-3.5" />                                                  <- selected listbox option
```

---

## F. LOADER ATLAS

### `loading-indicator` (utilities.css **141–143**) — color only, not a shape
```
@utility loading-indicator {
  @apply text-coollabs dark:text-warning;
}
```
`loading-indicator` now supplies **only the color** (coollabs purple / warning yellow). The spinner *shape* is always an inline arc SVG (below), tagged with this class plus `animate-spin` and a `size-*`:

### The arc spinner (canonical markup, `components/loading.blade.php`, verbatim)
```
<div {{ $attributes->merge(['class' => 'inline-flex items-center justify-center gap-2 text-[13px] text-neutral-500 dark:text-fg-dim']) }}
    role="status" aria-live="polite">
    <svg @class(['loading-indicator shrink-0 animate-spin', 'size-3' => $compact, 'size-4' => ! $compact]) viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle class="opacity-20" cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2" />
        <path class="opacity-80" d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
    </svg>
    @if (isset($text)) <span>{{ $text }}</span> @endif
</div>
```
Arc = faint full ring (`opacity-20`) + bright 3/4 arc (`opacity-80`), `stroke="currentColor"` so the class color tints it. Sizes by context: `size-3` (compact), `size-4` (default), `[&_.loading-indicator]:size-5` (table loading), `size-3.5` (pagination footer).

### Button loading swap
- `.button.is-loading > svg:not(.animate-spin) { display: none; }` (utilities.css **151–153**) — static icons hide while the inline spinner shows.
- `.button.is-loading { pointer-events: none; }` — no double-click.

### Spinner color overrides (app.css **378–419**)
`!important` overrides force the warning/theme color on spinners even when a parent tries to tint them.

### Placement patterns
| Surface | Pattern |
|---|---|
| Buttons | `x-loading-on-button` injects `<svg class="loading-indicator size-3.5 animate-spin">`; `wire:loading.attr="disabled"` + `wire:loading.class="is-loading"` |
| Table loading | `<x-loading aria-label class="[&_.loading-indicator]:size-5" />` in `wire:loading.flex wire:target` |
| Table search | leading search reicon `wire:loading.remove` ↔ arc svg `wire:loading` (same slot) |
| Pagination | inline `loading-indicator size-3.5 animate-spin` + `sr-only` "Loading page…", `aria-live="polite"` |
| Terminal connect | `size-3 animate-spin` arc next to "connecting…" / "reconnecting… (attempt N)" label |

---

## G. PAGINATION / OFFSET-CHANGER FOOTER (deep)

> Verified class bundles live in **§D — Pagination footer** above (footer, summary, `$buttonClass`,
> page-size trigger, custom input). This section covers the *behaviors*.

**Footer visibility**: footer hides entirely when `$total === 0` (`@if($total > 0)`); the table body
then shows the `empty` component instead.

**Summary block**: `<span class="inline-flex h-7 items-center whitespace-nowrap tabular-nums">{{ $from }}–{{ $to }} of {{ $total }}</span>` — en-dash, `tabular-nums` so digits don't jitter.

**Prev/Next**: single `$buttonClass` (verbatim in §D); prev icon = `<x-reicon name="arrow-right" class="size-3.5 rotate-180" />`, next = plain; `aria-label="Previous page"` / `"Next page"`; `@disabled` on first/last page; loading state swaps in `loading-indicator size-3.5 animate-spin` + `sr-only` "Loading page…" (`aria-live="polite"`).

**Page-size selector** (`components/page-size-select.blade.php`, Alpine):
- Options `[10, 25, 50, 100]` + **Custom…** row; custom row swaps the panel into a numeric input (`min="1" max="100" inputmode="numeric"`, `@keydown.enter` / `@keydown.escape` / `@blur` commit).
- `$commit()` clamps 1–100, persists to `localStorage` (per-page key), then either `$wire.set(model, value)` (Livewire mode) or updates the Alpine binding + `page = 1` (client mode).
- Panel is `x-table.dropdown panel-class="min-w-24!"`; options render as `listbox-option` rows with a `check` reicon on the selected one.
- Client-side variant (`client-pagination.blade.php`) filters an Alpine array instead of hitting the server.

## H. TERMINAL / CONSOLE SURFACES — verified current

The old `components/terminal.blade.php` no longer exists. Terminal lives in **Livewire**:
`resources/views/livewire/project/shared/terminal.blade.php` (+ `logs.blade.php`, `get-logs.blade.php`,
`process-dialog.blade.php`, `deployment/configuration-diff.blade.php`), with theme picker
`components/terminal/theme-selector.blade.php`.

- Root: `<div id="terminal-container" x-data="terminalData()" data-auto-start="...">`, Alpine machine `terminalData()`; listens `x-on:terminal-starting.window` and `x-on:terminal-theme-change.window`.
- Theme: `setTerminalTheme(localStorage.getItem('coolify-console-theme') ?? 'system')` — stored under `coolify-console-theme`.
- Keepalive: `<div class="hidden" wire:poll.keep-alive.30s="keepTerminalPageAlive">`.
- **Shell missing**: application console renders `<x-empty size="lg" title="Shell unavailable" description="This container does not include Bash or sh. Install a supported shell to use the terminal." icon-name="browser-terminal" />`; non-app variant shows a bordered panel with an alert-triangle svg + "Terminal Not Available".
- Fullscreen shell (verbatim):
```
terminal-fullscreen-shell fixed inset-0 z-[100000] m-0 flex w-screen max-w-none flex-col overflow-hidden rounded-none p-0
```
(z-[100000] — the single highest z in the app.) Non-app default: `relative flex w-full h-full max-h-[510px] flex-col py-4 mx-auto`; application console: `relative flex h-full min-h-0 w-full flex-col overflow-hidden bg-transparent`.
- Connect state: `x-show="!terminalActive"` overlay with `terminal-loading-label flex items-center gap-2` + `size-3 animate-spin` arc; label `x-text` shows `connecting…` / `reconnecting… (attempt N)` via `connectionState` / `reconnectAttempts`.
- Terminal scrollbar + chrome are the app.css blocks (~**435–891**); selection + theme vars driven by `--terminal-scrollbar` and `color-mix` (see Part III).

---

## I. MICRO-UTILITIES (the small stuff) — verified current

| Utility | Classes (verbatim) |
|---|---|
| `control-selected` | `bg-linear-to-b from-coollabs-100 to-coollabs-200 text-white` (utilities.css **137–139**) — active state for list/grid view toggles (shared-variables view-controls, list-search-controls) |
| `loading-indicator` | `text-coollabs dark:text-warning` (utilities.css **141–143**) — color only; shape = inline arc SVG |
| `icon-button` | `inline-flex size-7 shrink-0 items-center justify-center rounded-md border border-transparent text-neutral-400 outline-0 transition-colors hover:bg-neutral-100 hover:text-black focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent disabled:pointer-events-none disabled:opacity-35 dark:text-fg-faint dark:hover:bg-white/[0.07] dark:hover:text-fg` (utilities.css **146–148**) |
| `auth-tooltip` | `fixed z-[10000] px-2.5 py-1.5 text-xs font-medium rounded-lg pointer-events-none whitespace-nowrap text-white bg-neutral-900 border border-neutral-700 shadow-lg dark:text-fg dark:bg-raised dark:border-white/10` (utilities.css **165–167**) — the button tooltip bubble |
| `app-tab` / `app-tab-active` | pill tabs (see §D resource heading tabs), utilities.css **156–163** |
| `tag` | `px-2 py-1 cursor-pointer box-description dark:bg-coolgray-100 dark:hover:bg-coolgray-300 bg-neutral-100 hover:bg-neutral-200` (utilities.css **177–179**) |
| `icon` | `w-6 h-6 dark:hover:text-white` (utilities.css **271–273**) |
| `scrollbar` | `scrollbar-thumb-coollabs-100 scrollbar-track-neutral-200 dark:scrollbar-thumb-coollabs-100 dark:scrollbar-track-coolgray-200 scrollbar-thin` (utilities.css **275–277**) |
| `main` | `pt-4 pr-10 pl-24 lg:pr-32 lg:pl-44` (utilities.css **279–281**) |
| `custom-modal` | `flex z-50 flex-col gap-2 px-8 py-4 border dark:bg-coolgray-100 dark:border-coolgray-200` (utilities.css **283–285**) |
| `navbar-main` | `flex flex-col gap-4 justify-items-start pb-3 border-b border-solid h-fit md:flex-row sm:justify-between dark:border-white/[0.06] border-neutral-200 md:items-center text-neutral-700 dark:text-fg-dim` (utilities.css **287–289**) |
| `loading` | `w-4 dark:text-warning text-coollabs` (utilities.css **291–293**) |
| `kbd-custom` | `px-2 text-xs rounded-sm border border-dashed border-neutral-700 dark:text-warning` (utilities.css **295–297**) |
| `box` | `relative flex lg:flex-row flex-col p-3 transition-colors cursor-pointer min-h-[4rem] bg-white dark:bg-surface border text-black dark:text-fg hover:text-black border-neutral-200 dark:border-white/[0.06] hover:bg-neutral-50 dark:hover:bg-raised dark:hover:border-white/[0.1] dark:hover:text-fg hover:no-underline rounded-md` (utilities.css **299+**) |
| `text-helper` | `inline-block font-semibold text-coollabs dark:text-warning` (utilities.css **339–341**) |
| `info-helper` | `cursor-pointer text-neutral-400 transition-colors hover:text-neutral-600 dark:text-fg-faint dark:hover:text-fg-dim` (utilities.css **343–345**) |
| `info-helper-popup` | `rounded-lg border border-neutral-200 bg-white text-neutral-600 shadow-modal whitespace-normal break-words dark:border-white/10 dark:bg-raised dark:text-fg-dim` (utilities.css **347–349**) — the info bubble |
| `bg-coollabs-gradient` | `from-purple-500 via-pink-500 to-red-500 bg-linear-to-r` (utilities.css **335–337**) — the only gradient utility |
| `alert-success` / `alert-error` | `flex gap-2 items-center text-success` / `text-error` (utilities.css **169–175**) |
| `sr-only` | Tailwind default (paired with `aria-live="polite"` on async regions) |

**Micro-behaviors worth knowing**:
- All interactive list rows get `cursor-pointer` + hover surface + `transition-colors`.
- Number cells are `tabular-nums` (no jitter when counts change).
- Truncation: `truncate` + `min-w-0` + `max-w-[…]` on titles; `whitespace-nowrap` on table headers.
- Backdrops across overlays use `bg-black/50`-family + `backdrop-blur` (blur at backdrop, not panel).
- `rounded-md` = buttons/tabs/inputs; `rounded-lg` = tooltips/panels/pills; `rounded-[4px]` = checkboxes; `rounded-[10px]` = breadcrumb pill row; `rounded-full` = dots.
- Focus ring vocabulary: `focus-visible:ring-2 focus-visible:ring-offset-1` (buttons), `focus-visible:ring-1` + `ring-accent` (icon-button), `box-shadow: 0 0 0 1px var(--color-accent)` (input focus).

---

# PART III — Tweaks & Override-Pattern Inventory

## 1. The `!` (important) modifier — where and why

Tailwind v4's `!` suffix is the **escape hatch** for the CSS-first theme: a Blade bundle must beat a
`@utility`/unlayered app.css rule, so the parts that fight CSS get `!`. Catalog (all verified verbatim):

| Pattern | Where | Verbatim |
|---|---|---|
| Panel positioning overrides | table dropdown | `listbox-panel fixed! top-auto! right-auto! bottom-auto! z-[90]! mt-0!` |
| Panel positioning overrides | status-summary | `listbox-panel top-8! right-auto! left-0! z-[90]! w-[min(16rem,calc(100vw-1.5rem))]! min-w-0! sm:w-64! sm:min-w-64!` |
| Panel positioning overrides | breadcrumb-switcher | `listbox-panel scrollbar left-0! z-[90]! max-h-80! min-w-56 max-w-72` |
| Panel positioning overrides | resource-heading-overflow | `listbox-panel top-full! right-0! left-auto! mt-1! min-w-52!` |
| Panel width/min-width | table filter/sort | `panel-class="w-44! overflow-hidden! p-0!"` / `panel-class="w-44!"` |
| Panel min-width | page-size | `panel-class="min-w-24!"` |
| Panel option rows | status-summary rows | `listbox-option cursor-default! gap-2.5!` |
| Compact form sizes | page-size trigger | `h-7! w-12! border-0 px-1 text-[11px]! leading-none!` |
| Compact form sizes | page-size custom input | `mb-0! h-7! w-14! rounded-md! border-neutral-200! bg-transparent! px-1.5! py-0! text-[11px]! tabular-nums shadow-none! focus:border-neutral-300! focus:ring-0! dark:border-white/[0.08]! dark:text-fg-dim!` |
| Page title | dashboard navbar | `text-[24px]! leading-7! font-semibold! tracking-tight!` |
| Version chip | sidebar | `!text-[10.5px] ... !opacity-100 hover:!opacity-100` |
| Modal sizing | modal-input | `lg:w-[95vw]! lg:max-w-7xl!` |
| Modal height cap | modal | `modal-box max-h-[calc(100vh-5rem)]` |

Rule of thumb: **position/width/size that must beat a CSS class gets `!`; plain theme colors don't.**

## 2. Arbitrary `[&…]` variants (child targeting from Blade)

Because the CSS-first theme can't always express "style the child", blades use Tailwind arbitrary
variants to reach nested elements (all verified):

| Usage | Verbatim |
|---|---|
| Navbar | `[&_.button]:whitespace-nowrap` |
| Table loading | `[&_.loading-indicator]:size-5` |
| Settings dropdown | `[&_a]:font-medium` (plus `[&_a]:text-accent`-family tints) |
| Server metrics chart | `[&_.apexcharts-svg]:rounded-b-xl` (apexcharts root) |
| Select lazy mode | `[&>div]:h-full!` |

## 3. `color-mix()` inventory (app.css)

`color-mix()` is the theme-derivation primitive. Verified sites:

| Line(s) | Rule | Mix |
|---|---|---|
| 82 / 86 / 910 | terminal scrollbar border/bg | `in srgb, var(--terminal-scrollbar, #fff) 24%/22%/18%, transparent` |
| 955 | `--theme-bright-color` | `in srgb, var(--theme-base-color) 85%, white` |
| 956 | `--theme-scrollbar-thumb` | bright 70% + accent-foreground |
| 957 | `--theme-border-color` | `in oklab, var(--theme-base-color) 42%, #52525b` |
| 958 | `--theme-placeholder-color` | `in srgb, white 20%, base` |
| 961 | `--color-coollabs-100` | `in oklab, bright 88%, white` |
| 968 | `--color-panel` (custom theme) | `in oklab, var(--theme-base-color) 14%, #0c0c0d` |

Custom themes (app.css **935–989**) re-derive the whole token set from a single `--theme-base-color`:
accent → bright, warning → bright, panel/surface/raised/fg-dim/fg-faint/coollabs-* all via color-mix.

## 4. Dark-mode selector map

- **Root**: `@custom-variant dark (&:where(.dark, .dark *));` (app.css **15**) — class-based, driven by
  `<html class="dark">`. No `prefers-color-scheme` coupling for utilities.
- **Manual dark overrides** written as `.dark .x { … }` blocks (e.g. `.dark .data-table-header`,
  app.css **2131**) for CSS-only classes that can't take `dark:` variants.
- **Custom themes** bypass dark mode entirely via `html[data-theme="custom"]` (app.css **1030**-family)
  and the `--theme-*` derivation above.
- **Dark fill vocabulary** (consistent across every component): `dark:bg-surface` / `dark:bg-raised` /
  `dark:bg-white/[0.06–0.12]` for fills, `dark:border-white/[0.06–0.12]` for strokes,
  `dark:text-fg` / `-dim` / `-faint` for text, `dark:bg-warning` / `dark:text-black` for the
  light-in-dark flip (the inverse of Light's `bg-coollabs text-white`).

---

*End of deep-dive. All class strings quoted verbatim from the current Coolify source
(`resources/css/app.css`, `resources/css/utilities.css`, `resources/views/**`); line numbers cited
match the files at time of writing.*
