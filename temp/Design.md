# Coolify UI/UX Design System

> Extraction reference — a self-contained, adoptable design system documented from the
> [Coolify](https://github.com/coollabsio/coolify/) repository (`main` branch).
>
> Every claim below cites the exact repo file and line range it was extracted from.
> File paths are relative to the repository root. The document intentionally
> contains **no Coolify product content** — only the visual system, so any project
> can adopt it.
>
> Stack: Laravel + Livewire + Blade + Alpine.js + Tailwind CSS **v4** (CSS-first
> `@theme`, no `tailwind.config.js`) + `tw-animate-css` + `tailwind-scrollbar`
> (`resources/css/app.css:1-10`, `package.json`).

---

## 1. Theming & Dark Mode

- Class-based dark mode, defined once:
  `@custom-variant dark (&:where(.dark, .dark *));` — `resources/css/app.css:15`.
  Every `dark:` variant in the system resolves through this selector, so a single
  `.dark` class on `<html>` flips the entire theme.
- Native color-scheme is switched with the same class:
  `html { color-scheme: light }` / `html.dark { color-scheme: dark }`
  (`resources/css/app.css:119-127`).
- Document background: `html, body { @apply w-full min-h-full bg-gray-50 dark:bg-app dark:text-fg-dim; }`
  and `body { @apply text-sm font-sans antialiased scrollbar overflow-x-clip; min-height: 100dvh; }`
  (`resources/css/app.css:259-269`). Note `overflow-x: clip` (not `hidden`) — the
  comment at `app.css:264-267` explains `hidden` breaks `position: sticky`.
- Mobile input zoom guard: on `max-width: 767px` all `input/textarea/select` are
  forced to `font-size: 16px !important` (`resources/css/app.css:247-253`).

**The accent duality rule** (repeated across the whole system): light mode uses the
brand purple (`coollabs`), dark mode swaps to the readable yellow (`warning`).
This applies to focus rings, active tabs, the dirty-state bar, the highlighted
button, helper text, spinners, and status accents.

---

## 2. Design Tokens

All Tailwind theme tokens are declared in one `@theme` block:
`resources/css/app.css:17-68`.

### 2.1 Typography

| Token | Value | Source |
|---|---|---|
| `--font-sans` | `'Geist Sans', Inter, sans-serif` | `app.css:18` |
| `--font-mono` | `'Geist Mono', 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace` | `app.css:19` |
| `--font-geist-sans` | `'Geist Sans', Inter, sans-serif` | `app.css:20` |
| `--font-logs` | mono stack (log/terminal surfaces) | `app.css:21` |

Geist Sans/Mono variable fonts are bundled in `resources/fonts/` and wired via
`resources/css/fonts.css` (imported at `app.css:1`).

Global heading scale (`resources/css/app.css:295-300`):
- `h1` → `text-[24px] leading-7 font-semibold tracking-tight dark:text-white`
- `h2` → `text-xl font-bold dark:text-white`

UI text scale used across components: **13px** for controls/buttons/menus,
**12px** for helper/meta text, **11px** for footers/badges, **10px** for tiny pills.

### 2.2 Color tokens

| Token | Value | Usage | Source |
|---|---|---|---|
| `--color-base` | `#101010` | near-black canvas base | `app.css:23` |
| `--color-warning` | `#fcd452` (+ full 50–900 scale) | dark-mode accent, warnings | `app.css:24-34` |
| `--color-success` | `#22C55E` | success | `app.css:35` |
| `--color-error` | `#dc2626` | error | `app.css:36` |
| `--color-coollabs` | `#6b16ed` (50–300 scale) | brand purple, light-mode accent | `app.css:37-41` |
| `--color-coolgray-100…500` | `#181818 #202020 #242424 #282828 #323232` | legacy neutral surface scale | `app.css:42-46` |

### 2.3 Graphite surface tokens (layered neutrals)

Comment at `app.css:48-49`: *"Graphite design language (ported from
ref/frontend). Layered neutral surfaces + translucent hairlines. See DESIGN.md."*

| Token | Value | Usage | Source |
|---|---|---|---|
| `--color-app` | `#0c0c0d` | page canvas (dark) | `app.css:50` |
| `--color-panel` | `oklch(10% 0 0)` | top-bar/nav surface, neutral near-black | `app.css:52` |
| `--color-surface` | `#161618` | cards / nested panels | `app.css:53` |
| `--color-raised` | `#1c1c1e` | raised shells, dropdowns | `app.css:54` |
| `--color-selected` | `#26262a` | selected rows | `app.css:55` |
| `--color-fg` | `#f2f2f2` | primary text | `app.css:56` |
| `--color-fg-dim` | `#b4b4b8` | secondary text | `app.css:57` |
| `--color-fg-faint` | `#6e6e74` | muted text, disabled | `app.css:58` |
| `--color-accent` | `#6b16ed` | focus rings, active borders | `app.css:59` |
| `--color-accent-foreground` | `#ffffff` | text on accent | `app.css:60` |
| `--color-hairline` | `rgba(255, 255, 255, 0.08)` | hairline borders | `app.css:61` |
| `--color-nav-text` | `#525252` | nav item text | `app.css:62` |
| `--color-nav-muted` | `#666666` | nav section headers | `app.css:63` |
| `--color-nav-active` | `#171717` | nav active text | `app.css:64` |
| `--color-log` | `#0d0d0d` | log/terminal canvas | `app.css:65` |
| `--shadow-modal` | `0 24px 64px rgba(0,0,0,0.55), 0 4px 16px rgba(0,0,0,0.4)` | modal/floating elevation | `app.css:67` |

### 2.4 Coollabs CSS-variable surface ladder

A parallel theming ladder of `--coollabs-*` variables, re-derived per theme
(`resources/css/app.css:924-945`), and overridden by the Graphite tokens when a
custom theme is active (`app.css:977-992`):

| Var | Light | Dark | Use |
|---|---|---|---|
| `--coollabs-canvas` | `oklch(98.75% 0 0)` | `oklch(10% 0 0)` | page canvas |
| `--coollabs-elevated` | `oklch(98% 0 0)` | `oklch(15% 0 0)` | shells, card headers |
| `--coollabs-recessed` | `oklch(96% 0 0)` | `oklch(20% 0 0)` | inputs, listboxes |
| `--coollabs-base` | `#ffffff` | `oklch(17% 0 0)` | nested card bodies |
| `--coollabs-fill` | `oklch(92.2% 0 0)` | `oklch(26.9% 0 0)` | dividers, passive fills |
| `--coollabs-line` | `oklch(14.5% 0 0 / 0.1)` | `oklch(32% 0 0)` | control borders |
| `--coollabs-hairline` | `oklch(93.5% 0 0)` | `oklch(26.9% 0 0)` | shell rings |
| `--coollabs-subtle` | `oklch(55.6% 0 0)` | `oklch(70.8% 0 0)` | muted labels |

The card idiom these enable: **elevated shell + 1px hairline ring + nested base
body + 1px fill ring** (see `.application-settings-section`, §8.4).

### 2.5 Motion tokens

- Custom spinner-track keyframes `lds-heart` and `coolbox-border-track`
  (`app.css:138-204`); the coolbox loading border animation runs 2400ms linear
  (`app.css:164-226`).
- Standard overlay motion timing ladder — see §10.

---

## 3. Core Primitives (CSS utilities)

All custom utilities live in `resources/css/utilities.css` as Tailwind v4
`@utility` blocks. These are the atomic design tokens for components.

### 3.1 Buttons

- **`@utility button`** (`utilities.css:128-131`) — the single default button:
  `inline-flex shrink-0 gap-1.5 justify-center items-center whitespace-nowrap
  px-2.5 h-9 min-h-9 text-[13px] text-black normal-case rounded-md border
  outline-0 cursor-pointer font-medium transition-colors bg-white
  border-neutral-200 hover:bg-neutral-100 dark:bg-white/[0.06] dark:text-fg
  dark:hover:bg-white/[0.1] dark:border-white/[0.08] hover:text-black
  disabled:cursor-not-allowed min-w-fit dark:disabled:text-fg-faint
  disabled:border-neutral-200 dark:disabled:border-white/[0.06]
  disabled:hover:bg-transparent disabled:bg-transparent
  disabled:text-neutral-300 focus-visible:outline-none focus-visible:ring-1
  focus-visible:ring-accent`.
  - Height `h-9` intentionally matches `.input`/`.select` (comment at
    `utilities.css:129`) so side-by-side actions stay equal height.
- **`@utility button-highlighted`** (`utilities.css:133-135`) — primary variant:
  `border-coollabs-200 bg-linear-to-b from-coollabs-100 to-coollabs-200
  text-white! hover:from-coollabs-100 hover:to-coollabs hover:text-white!`.
  In dark mode the purple still reads as the primary (the accent swap to
  `warning` is reserved for active/focus states, not this fill).
- **Attribute variants** (`resources/css/app.css:287-293`):
  - `button[isError]:not(:disabled)` → `text-red-800 dark:text-red-300 bg-red-50
    dark:bg-red-900/30 border-red-300 dark:border-red-800 hover:bg-red-300
    hover:text-white dark:hover:bg-red-800 dark:hover:text-white` (destructive).
  - `button[isHighlighted]:not(:disabled)` → `@apply button-highlighted`.
  - Both attributes pass through Blade components as bare HTML attributes and
    are styled purely by these CSS selectors.
- **Loading state**: Livewire adds `wire:loading.class="is-loading"`; CSS hides
  static icons while the spinner shows:
  `.button.is-loading > svg:not(.animate-spin) { display: none }`
  (`utilities.css:151-153`).
- **`@utility icon-button`** (`utilities.css:146-148`) — compact icon-only
  control: `inline-flex size-7 shrink-0 items-center justify-center rounded-md
  border border-transparent text-neutral-400 outline-0 transition-colors
  hover:bg-neutral-100 hover:text-black focus-visible:outline-none
  focus-visible:ring-1 focus-visible:ring-accent disabled:pointer-events-none
  disabled:opacity-35 dark:text-fg-faint dark:hover:bg-white/[0.07]
  dark:hover:text-fg`.

### 3.2 Inputs & selects

- **`@utility input-select`** (`utilities.css:61-76`) — shared base for both:
  `block h-9 px-3 py-1.5 w-full text-sm text-black rounded-md border
  border-neutral-200 bg-white dark:bg-surface dark:text-fg
  dark:border-white/[0.08] transition-colors disabled:bg-neutral-100
  disabled:text-neutral-400 dark:disabled:bg-white/[0.03]
  dark:disabled:text-fg-faint`.
- **`@utility input`** (`utilities.css:79-101`) — `input-select` + read-only and
  placeholder styling. **Focus language** (repeated everywhere):
  `border-color: var(--color-accent); box-shadow: 0 0 0 1px var(--color-accent)`
  (lines 84-92). Read-only clears the shadow (`input:read-only { box-shadow: none }`).
- **`@utility select`** (`utilities.css:103-126`) — `input-select` with a
  **data-URI chevron background** (dark `#000` SVG in light mode, white SVG in
  dark at lines 113-115), `padding-right: 2.5rem`, same accent focus language.
  No custom arrow markup needed.
- **`@utility input-sticky`** (`utilities.css:34-49`) — legacy “sticky” input
  with a 4px inset left accent bar + 1px outline:
  `box-shadow: inset 4px 0 0 transparent, inset 0 0 0 1px #e5e5e5`
  (dark `#242424`); on `:focus-visible` the bar becomes `#6b16ed` light /
  `#fcd452` dark (lines 42-48). **This is the ancestor of the system-wide dirty
  state** (§3.5).
- **`@utility input-focus`** (`utilities.css:56-58`) — ring focus helper:
  `focus-visible:ring-2 focus-visible:ring-coollabs dark:focus-visible:ring-warning
  focus-visible:ring-offset-2 dark:focus-visible:ring-offset-base`.

### 3.3 Navigation primitives

- **`@utility menu-item`** (`utilities.css:225-227`): `relative flex gap-2.5
  items-center h-8 px-2.5 w-full text-[13px] font-medium rounded-md truncate
  min-w-0 transition-colors text-nav-text hover:bg-neutral-100
  hover:text-nav-active dark:hover:bg-white/[0.05]`.
- **`menu-item-icon`** (`:228-230`): `shrink-0 size-[18px] opacity-90`.
- **`menu-item-label`** (`:232-234`): `min-w-0 flex-1 truncate`.
- **`@utility menu-item-active`** (`:236-239`) — **solid neutral fill only, no
  accent rail/border**: `overflow-hidden rounded-md bg-black/[0.05]
  text-nav-active hover:bg-black/[0.05] dark:bg-white/[0.06]
  dark:hover:bg-white/[0.06]`. The comment at `app.css:90-108` enforces this by
  killing any legacy gradient/rail.
- **`nav-section`** (`:242-244`): `px-2.5 pt-1 pb-1 text-[11px] font-medium
  text-nav-muted select-none` (subtle title-case group header).
- **`menu-subitem` / `menu-subitem-active`** (`:247-253`): indented child rows
  (`pl-3`), same active fill rule.
- **`sub-menu-wrapper` / `sub-menu-item` / `sub-menu-item-icon`** (`:255-265`):
  flyout sub-menu row set (compact `w-52` column).
- **Collapsed sidebar** (`utilities.css:407-422`): under `@media (min-width: 1024px)`,
  `.sidebar-collapsed .menu-item` becomes a centered `2rem` square
  (`width/height: var(--button-h, 2rem)`, `padding 0`, `margin-inline: auto`),
  and `.sidebar-collapsed-label` hides.
- **`user-menu-item`** (`:185-187`): avatar-menu row, `h-8 px-3 text-[13px]`.
- **`dropdown-item`** family (`:189-199`): `text-xs`, hover
  `bg-neutral-100 dark:hover:bg-coollabs` (a **solid purple hover** — the one
  place the accent is used as a hover fill), plus touch (`min-h-10`) and
  no-padding variants.
- **`scrollbar`** (`:275-277`): `scrollbar-thumb-coollabs-100
  scrollbar-track-neutral-200 dark:scrollbar-thumb-coollabs-100
  dark:scrollbar-track-coolgray-200 scrollbar-thin` (tailwind-scrollbar plugin).

### 3.4 Tabs & badges

- **`@utility app-tab`** (`utilities.css:156-158`): `inline-flex items-center
  gap-1 h-7 px-2.5 rounded-md text-[13px] font-medium text-neutral-500
  dark:text-fg-dim hover:bg-neutral-100 dark:hover:bg-white/[0.05]
  hover:text-black dark:hover:text-fg transition-colors` (6px radius, not full-round).
- **`@utility app-tab-active`** (`:161-163`): `bg-coollabs/10 text-coollabs
  shadow-sm ring-1 ring-coollabs/25 hover:bg-coollabs/15 dark:bg-warning/15
  dark:text-warning dark:ring-warning/25 dark:hover:bg-warning/20` — tinted
  accent pill with inset ring. Canonical usage pairs it with
  `aria-current="page"` (`resources/views/livewire/server/navbar.blade.php:249-256`).
- Legacy heading-action scoping `.application-heading-actions .app-tab`
  (`app.css:1761-1838`): `height:1.75rem; padding:0 .625rem; border-radius:6px;
  font-size:13px; font-weight:500; color:#737373`; active
  `[aria-current='page']` → `background: color-mix(in srgb, var(--color-coollabs)
  10%, transparent); color: var(--color-coollabs); box-shadow: inset 0 0 0 1px
  color-mix(in srgb, var(--color-coollabs) 25%, transparent)` (dark: `warning`).
- **`@utility badge`** (`:201-203`): `inline-block w-3 h-3 text-xs font-bold
  rounded-full leading-none border border-neutral-200 dark:border-black`;
  `badge-dashboard` (`:205-207`) is the absolute-positioned corner variant;
  `badge-success/warning/error` (`:209-219`) set `bg-success/warning/error`.
- **`@utility tag` / `add-tag`** (`:177-183`): removable chip + “add tag” row.

### 3.5 System-wide state affordances

- **Dirty/unsaved state** — the single most consistent signal:
  `wire:dirty.class="[box-shadow:inset_4px_0_0_#6b16ed,inset_0_0_0_2px_#e5e5e5]
  dark:[box-shadow:inset_4px_0_0_#fcd452,inset_0_0_0_2px_#242424]"`
  — a 4px left accent bar (purple light / yellow dark) plus a 2px outline.
  Present on every wired input (`forms/input.blade.php`, `forms/textarea.blade.php`,
  `forms/select.blade.php`, `forms/env-var-input.blade.php`), and as equivalent
  Alpine `:style` logic in `forms/datalist.blade.php`.
- **Loading state**: `wire:loading.attr="disabled"` on all inputs/selects/
  checkboxes; `opacity-50`/`opacity-70` fade variants on listbox containers.
- **`text-helper`** (`utilities.css:339-341`): `inline-block font-semibold
  text-coollabs dark:text-warning` — used by `<x-highlighted>` for the required
  `*` star.
- **`info-helper` / `info-helper-popup`** (`:343-349`): the `?` popover pair
  (see §4.16).
- **`auth-tooltip`** (`:165-167`): `fixed z-[10000] px-2.5 py-1.5 text-xs
  font-medium rounded-lg pointer-events-none whitespace-nowrap text-white
  bg-neutral-900 border border-neutral-700 shadow-lg dark:text-fg dark:bg-raised
  dark:border-white/10`.

### 3.6 Cards & misc

- **`@utility box`** (`utilities.css:299-301`) — clickable list-card:
  `relative flex lg:flex-row flex-col p-3 transition-colors cursor-pointer
  min-h-[4rem] bg-white dark:bg-surface border text-black dark:text-fg
  hover:text-black border-neutral-200 dark:border-white/[0.06] hover:bg-neutral-50
  dark:hover:bg-raised dark:hover:border-white/[0.1] dark:hover:text-fg
  hover:no-underline rounded-md`.
- **`@utility coolbox`** (`:315-317`) — larger rounded card (`rounded-2xl`,
  `hover:shadow-[0_4px_16px_rgba(0,0,0,0.35)]`).
- **`box-boarding` / `box-without-bg` / `box-without-bg-without-border`**
  (`:303-313`) — onboarding and ghost variants.
- **`box-title` / `box-description` / `description`** (`:323-333`) — card
  typography trio.
- **`kbd-custom`** (`:295-297`): `px-2 text-xs rounded-sm border border-dashed
  border-neutral-700 dark:text-warning`.
- **Log surface utilities** (`:380-405`): `log-line` (content-visibility
  optimization), `log-highlight` (search highlight), `log-error/warning/debug/info`
  (per-level background tints).
- **Chart tooltip overrides** `apexcharts-tooltip-*` (`:1-32`) restyle ApexCharts
  tooltips to the neutral card language.
- **`heading-item-active`** (`:267-269`): `text-black rounded-sm dark:bg-coolgray-200
  dark:text-warning`.

---

## 4. Form Components

Source: `resources/views/components/forms/*.blade.php` (resolve default classes in
`app/View/Components/Forms/*.php`).

### 4.1 Shared patterns (cross-cutting)

- **Label row** (identical in input, textarea, select, listbox,
  searchable-listbox, env-var-input, domain-input):
  ```html
  <div class="mb-1.5 flex h-4 w-full items-center gap-1.5">
    <label class="mb-0! flex items-center gap-1 text-sm font-medium leading-4">
      … <x-highlighted text="*" />
    </label>
    <x-helper :helper="$helper" />
  </div>
  ```
  Fixed `h-4` aligns labels with the helper icon; `mb-0!` overrides
  `.application-settings-form` label margins.
- **Error block** (shared): `<label class="label"><span class="text-red-500
  label-text-alt">…</span></label>` — **caveat**: `.label` / `.label-text-alt`
  are orphaned daisyUI-era classes with no CSS in the repo; only `text-red-500`
  renders. Do not adopt them.
- **Dirty state** — see §3.5.
- **Height system**: all controls are 32px rows (`h-9`/`min-h-9` for
  `.button`/`.input`/`.select`, `.chip-input` min-height 2rem, `.listbox-trigger`
  2.25rem). **No size variants (sm/md/lg) exist** — size is fixed by CSS, never
  parameterized in Blade.

### 4.2 Checkbox — `forms/checkbox.blade.php`

- Row: `form-control group flex min-h-9 max-w-full items-center rounded-lg px-2.5
  py-1.5 transition-colors`, hover `hover:bg-neutral-100/80
  dark:hover:bg-white/[0.035]`, disabled `opacity-55`.
- Hidden native input: `peer absolute inset-0 z-10 m-0 h-full w-full
  cursor-pointer appearance-none opacity-0 disabled:cursor-not-allowed`.
- Custom box (`size-[18px]`, radius `rounded-[5px]`):
  `pointer-events-none absolute inset-0 rounded-[5px] border border-neutral-300
  bg-white shadow-[inset_0_1px_1px_rgb(0_0_0/0.04)] transition-colors
  group-hover:border-neutral-400 peer-checked:border-coollabs peer-checked:bg-coollabs
  peer-focus-visible:ring-2 peer-focus-visible:ring-coollabs/25
  peer-focus-visible:ring-offset-2 peer-disabled:opacity-50 dark:border-white/[0.14]
  dark:bg-white/[0.045] dark:shadow-none dark:group-hover:border-white/[0.22]
  dark:peer-checked:border-warning dark:peer-checked:bg-warning
  dark:peer-focus-visible:ring-warning/30 dark:peer-focus-visible:ring-offset-base`.
- Check mark: `size-3`, scale-in on `peer-checked`, `text-white dark:text-black`,
  path `m2.25 6.15 2.35 2.3 5.15-5`, stroke-width 1.8.
- Accent: purple checked fill in light, yellow in dark.

### 4.3 Text input — `forms/input.blade.php`

- Root `w-full` (or `flex-1` for multiline). Input class: `input`.
- Password variant wraps in `<div class="relative" x-data="{ type: 'password' }">`;
  toggle: `password-toggle flex absolute inset-y-0 right-0 z-10 items-center pr-2
  cursor-pointer text-neutral-500 hover:text-black dark:text-neutral-400
  dark:hover:text-white` with `<x-reicon name="eye">`/`eye-off2` at `size-[18px]`,
  `aria-label="Toggle password visibility"`. Input gains
  `input-with-password-toggle` (`app.css:362-370`).
- Focus comes **only** from the `input` utility (accent border + 1px shadow) —
  no Tailwind ring on the input itself.

### 4.4 Textarea — `forms/textarea.blade.php`

- Class `input scrollbar` (+ `font-mono` when `monospace`). Tab key inserts two
  spaces (`@keydown.tab`). Monaco delegation via `x-forms.monaco-editor` when
  `monaco` mode; height driven by inline `--editor-height`.

### 4.5 Select — `forms/select.blade.php`

- Native `<select class="select w-full">`; chevron is a CSS data-URI background
  (see §3.2), `padding-right: 2.5rem`. Slot renders `<option>` children.

### 4.6 Listbox — `forms/listbox.blade.php` (custom Alpine select)

- Trigger: `class="listbox-trigger"` + `aria-haspopup="listbox"` +
  `:aria-expanded="open"` + `:title="current"` (tooltip shows current value).
  Chevron-up-down SVG `size-3.5 shrink-0 opacity-60`, stroke-width 2.
- Panel: `class="listbox-panel"` + `role="listbox"` + transition classes:
  `enter: transition ease-out duration-100`, `enter-start: opacity-0 -translate-y-1
  scale-[0.98]`, `leave: transition ease-in duration-75`.
- Options: `class="listbox-option" role="option" :aria-selected` + check SVG on
  selected (`size-3.5`, stroke-width 2.5, path `m4.5 12.75 6 6 9-13.5`).
- Empty state: `px-3 py-2 text-[13px] text-neutral-500 dark:text-fg-dim`.
- Saving state: whole control gets `pointer-events-none opacity-70`.
- CSS (`app.css:1872-1995`): `.listbox-trigger` height 2.25rem; `.listbox-panel`
  `position:absolute; top:calc(100% + .25rem); z-index:30; display:flex;
  flex-direction:column; gap:1px; min-width:max(100%,13rem); width:max-content;
  max-width:min(24rem, calc(100vw - 1.5rem)); max-height:16rem; padding:.25rem;
  border-radius:10px; border:1px solid var(--coollabs-line);
  background:var(--coollabs-recessed); box-shadow:0 12px 32px rgba(0,0,0,.45)`;
  `.listbox-option` `min-height:2rem; padding:.375rem .5rem; border-radius:6px;
  font-size:.875rem`, hover `background: var(--coollabs-fill)`, disabled
  `opacity:.4; cursor:not-allowed`.
- Portal mode positions the panel `fixed` with `z-index:9999` and JS
  `positionPanel($el)`.

### 4.7 Searchable listbox — `forms/searchable-listbox.blade.php`

- Panel: `listbox-panel searchable-listbox-panel` (no transition).
- Search bar `.searchable-listbox-search` with leading `<x-reicon name="search"
  class="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2
  text-neutral-400 dark:text-fg-faint">` and input
  `.searchable-listbox-search-input` (`height:2rem; border-radius:6px; border:1px
  solid var(--coollabs-line); background:var(--coollabs-recessed); padding:0 .5rem
  0 2rem; font-size:.8125rem`; focus uses the accent language — `app.css:1998-2063`).

### 4.8 Datalist — `forms/datalist.blade.php` (multi/single tag select)

- Multi-mode container has an inline checkbox per option (identical peer-styled
  box as §4.2) and tag chips: `inline-flex items-center gap-1.5 px-2 py-0.5
  text-xs bg-coolgray-200 dark:bg-coolgray-700 rounded whitespace-nowrap`,
  hover `hover:bg-red-100 dark:hover:bg-red-900/20 hover:text-red-600
  dark:hover:text-red-400` (removal affordance), `aria-label="Remove"`.
- Dropdown: `absolute z-50 w-full mt-1 bg-white dark:bg-coolgray-100 border
  border-neutral-300 dark:border-coolgray-400 rounded shadow-lg max-h-60
  overflow-auto scrollbar`; options `px-3 py-2 cursor-pointer hover:bg-neutral-100
  dark:hover:bg-coolgray-200 flex items-center gap-3`; selected row tint
  `bg-neutral-50 dark:bg-coolgray-300`.
- Focus is driven by Alpine `:style` computing the same inset-bar shadow as the
  dirty state (`#6b16ed`/`#fcd452` accent, `#e5e5e5`/`#242424` outline).

### 4.9 Env-var input — `forms/env-var-input.blade.php`

- `class="input"` + password-toggle support; suggestion dropdown reuses
  `.listbox-panel` with `top-full! z-[60]! mt-1! w-full! min-w-0! max-w-full!`.
- Suggestion rows: `listbox-option justify-start! gap-2.5!` with mono labels
  (`font-mono text-sm`), selected `bg-neutral-100 dark:bg-white/[0.08]`.
- Type badges: SCOPE → `rounded-md border border-warning/25 bg-warning/10 px-1.5
  py-0.5 text-[10px] font-semibold tracking-wide text-warning`; VAR →
  `border-emerald-500/25 bg-emerald-500/10 … text-emerald-600 dark:text-emerald-400`.

### 4.10 Domain input — `forms/domain-input.blade.php`

- Grid: `grid gap-4 sm:grid-cols-[8rem_minmax(0,1fr)_8rem]` (protocol / host /
  port) with full-width path row (`sm:col-span-3`). Protocol is a portal listbox.

### 4.11 Chips — `forms/domain-chips.blade.php`

- Container `class="chip-input"` (CSS `app.css:3526-3614`: min-height 2rem, radius
  8px, matches 32px row height). Chips `class="chip"` (height 1.5rem, radius 6px)
  with remove button `class="chip-remove"` + X SVG `size-3` stroke-width 2
  (path `M6 18 18 6M6 6l12 12`). Enter/comma commits, Backspace on empty removes.

### 4.12 Copy input — `forms/copy-button.blade.php`

- Readonly `input input-with-copy-button bg-white dark:bg-coolgray-100
  dark:read-only:bg-coolgray-100 dark:read-only:text-white` + select-on-focus +
  paste/cut/drop blocked. Copy button: `copy-button flex absolute inset-y-0
  right-0 z-10 items-center pr-2 cursor-pointer text-neutral-500 transition-colors
  hover:text-black focus-visible:ring-2 focus-visible:ring-coollabs
  focus-visible:ring-offset-2 dark:text-neutral-400 dark:hover:text-white
  dark:focus-visible:ring-warning dark:focus-visible:ring-offset-base`; icons
  `size-[18px]` copy / green check.

### 4.13 Monaco editor — `forms/monaco-editor.blade.php`

- Wrapper `coolify-monaco-editor flex-1` (border-radius 10px, 1px
  `--coollabs-line` border — `app.css:271-281`). Default height
  `calc(100vh - 20rem)`, min 150px, `--editor-height` override.
- Custom `coolify-dark` theme: editor/background/gutter `#0b0b0c`; scrollbar
  slider `#ffffff1a`/`#ffffff2e`/`#ffffff40`. Light mode uses Monaco stock `vs`,
  toggled live via MutationObserver on `<html>` class.
- Config: `wordWrap:'on'`, `minimap:false`, `fontSize:15`,
  `renderLineHighlight:'none'`, `stickyScroll:false`, padding 12/12, 8px
  no-shadow scrollbars.

### 4.14 Form button — `forms/button.blade.php`

- Default class `button` (`''` when `noStyle`); loading emits
  `wire:loading.attr="disabled"` + `wire:loading.class="is-loading"` and injects
  `<x-loading-on-button>`.
- Tooltip wrapper: when `authDisabled`/`tooltip`, wrapped in
  `<span class="relative inline-flex" x-data="{…}">` with
  `@mouseenter="showTooltip(300)"`, `@focusin="showTooltip()"`; tooltip element
  `class="auth-tooltip" role="tooltip"`.

### 4.15 Loading-on-button — `forms/loading-on-button.blade.php`

- `<span class="inline-flex shrink-0 items-center gap-1.5">` + spinner SVG
  `size-3.5 shrink-0 animate-spin`, circle `opacity-25 stroke-width=3`, arc path
  `opacity-75` `d="M21 12a9 9 0 0 0-9-9" stroke-linecap=round`.
  In dark mode `.dark .animate-spin { color: var(--color-warning) !important }`
  (`app.css:377-379`) turns spinners yellow.

### 4.16 Helper popover — `helper.blade.php`

- Trigger: `info-helper relative inline-flex shrink-0 items-center justify-center
  border-0 bg-transparent p-0 leading-none size-3.5` + `data-icon-tooltip-ignore`
  + `aria-label` (default “More information”). Icon: `<x-reicon name="info-circle"
  class="size-3.5 text-neutral-400 … dark:text-fg-faint">`.
- Popup: `info-helper-popup fixed z-[10000] w-max max-w-[min(20rem,calc(100vw-2rem))]
  whitespace-normal` + `role="tooltip"` + JS viewport-flipped positioning;
  inner `px-3 py-2.5 text-[13px] leading-5` (raw HTML allowed).
- Transitions: `enter: transition ease-out duration-100` with
  `opacity-0 translate-y-0.5` → `opacity-100 translate-y-0`; leave
  `ease-in duration-75`.

### 4.17 Icon tooltip — `icon-tooltip.blade.php`

- Global singleton (`<div class="contents">`) that auto-hijacks icon-only buttons
  (`button[title], a[title], [data-tooltip]` with an SVG child or
  `.icon-button`), converting `title` → `data-icon-tooltip` + `aria-label`.
- Tooltip element: `pointer-events-none fixed z-[10000] whitespace-nowrap
  rounded-lg border border-neutral-700 bg-neutral-900 px-2 py-1 text-xs
  font-medium text-white shadow-lg dark:border-white/10 dark:bg-raised` +
  `-translate-y-full` (flips below when `< 48px` from top, viewport-clamped 8px).

### 4.18 Icon copy button — `copy-button.blade.php`

- `inline-flex size-6 shrink-0 items-center justify-center rounded-md
  text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-black
  disabled:pointer-events-none disabled:opacity-40 dark:text-fg-dim
  dark:hover:bg-white/[0.06] dark:hover:text-white`; icons `size-3.5` copy /
  green check, 1000ms reset.

### 4.19 Highlighted — `highlighted.blade.php`

- `<span class="text-helper">{{ $text }}</span>` — the required `*` star
  (purple light / yellow dark).

---

## 5. Overlays & Feedback

Source: `resources/views/components/*.blade.php` (modal family, slide-over,
popup, toast, callout, banner, loading, empty, etc.).

### 5.1 z-index tier ladder

| z-index | Used by |
|---|---|
| `z-40` | trigger wrapper while its modal is open (`:class="{ 'z-40': modalOpen }"`) |
| `z-50` | generic dropdown panel, confirm-modal container |
| `z-[90]!` | table dropdown listbox panel (with `!important` overrides) |
| `z-99` | **modal family overlays** (modal-confirmation, modal-input, process-dialog, domain-conflict-modal, slide-over) |
| `z-999` | banner, popup, popup-small |
| `z-[1000]` | unsaved-bar |
| `z-[1100]` | configuration-warning popover |
| `z-9999` | toast container |
| `z-[10000]` | tooltips (auth-tooltip, icon-tooltip, info-helper-popup, listbox portal) |

### 5.2 Backdrop recipes

- **Standard modal**: `fixed inset-0 z-99` overlay + backdrop
  `absolute inset-0 bg-black/50 backdrop-blur-[2px]` (modal-confirmation,
  modal-input, domain-conflict-modal). No click-to-close on backdrop; close via
  Escape or close button.
- **Process dialog**: `bg-black/50 backdrop-blur-[2px] dark:bg-black/60`,
  click-to-close unless `closeWithX`.
- **Slide-over**: `fixed inset-0 dark:bg-black/60 backdrop-blur-xs` —
  **transparent in light mode** by design.
- **Legacy confirm-modal**: `fixed inset-0 bg-slate-900/75` (no blur).

### 5.3 Modal shell (canonical family)

All modern modals reuse the layer-card idiom:
- Panel: `application-settings-form application-settings-section relative flex
  max-h-[calc(100dvh-2rem)] w-full flex-col` + inline
  `style="box-shadow: 0 0 0 1px var(--coollabs-hairline), var(--shadow-modal)"`.
  Widths: modal-confirmation/domain-conflict → `lg:min-w-[36rem] lg:max-w-2xl`;
  modal-input default → `lg:w-auto lg:min-w-2xl lg:max-w-4xl`, large →
  `lg:w-[95vw]! lg:max-w-7xl!`.
- Header: `<header class="flex-nowrap!">` with `<h3 class="min-w-0 flex-1
  truncate">` (styled by `.application-settings-section > header`, §8.4).
- Body: `application-settings-section-body min-h-0 flex-1 overflow-y-auto`.
- Footer rows: `mt-4 flex flex-wrap justify-end gap-2 border-t border-neutral-200
  pt-4 dark:border-white/[0.08]`.
- **Panel motion** (enter/leave, identical across the family):
  `x-transition:enter="ease-out duration-100"` `enter-start="opacity-0
  -translate-y-2 sm:scale-95"` `enter-end="opacity-100 translate-y-0
  sm:scale-100"` `leave="ease-in duration-100"` with the mirrored start/end.
- **Focus trap**: `x-trap.inert.noscroll="modalOpen"` on every modern modal.
- Backdrop fade (modal-input only): `ease-out duration-100` opacity 0→100.
- **Process-dialog** differs: `min-h-[min(70dvh,28rem)] h-[min(85dvh,52rem)]`,
  widths by `$size` (`md`: `max-w-2xl sm:min-w-[28rem]`; `xl`: `max-w-5xl
  sm:min-w-[36rem] lg:min-w-[48rem]`; default `max-w-4xl sm:min-w-[32rem]
  lg:min-w-[42rem]`), enters **from below** (`translate-y-2`), and is the **only
  overlay with full dialog semantics**: `role="dialog" aria-modal="true"
  aria-labelledby="process-dialog-title"`.

### 5.4 Slide-over — `slide-over.blade.php`

- Teleported (`x-teleport="body"`), shell `relative z-99`. Panel widths
  `max-w-xl w-screen` / `max-w-4xl w-screen` (fullScreen). Inner shell:
  `flex flex-col h-full py-6 overflow-hidden border-l shadow-lg bg-neutral-50
  dark:bg-base dark:border-neutral-800 border-neutral-200`.
- Motion: `x-transition:enter="transform transition ease-in-out duration-100
  sm:duration-300"` `enter-start="translate-x-full"` (slide from right edge).
- Close: Escape / backdrop click / `@click.away` (unless `closeWithX`); close
  button `w-8 h-8 rounded-full` with `focus-visible:ring-2 ring-coollabs
  dark:ring-warning ring-offset-2 dark:ring-offset-base`.

### 5.5 Toast — `toast.blade.php`

- Container: `fixed z-9999 flex w-[calc(100%-2rem)] gap-2.5 sm:max-w-[26rem]`,
  **6 positions** (top/bottom × left/center/right; bottom stacks newest at the
  edge via `flex-col-reverse`).
- Item: `relative flex w-full items-start rounded-lg group` + inline
  `background: var(--coollabs-elevated); box-shadow: 0 0 0 1px
  var(--coollabs-line), var(--shadow-modal)`; padding `p-3.5 pr-20` (raw HTML
  mode `p-0`).
- Per-type icon chip (`size-8 rounded-lg`):
  - success: `bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400` + `check-circle`
  - info: `bg-coollabs/10 text-coollabs dark:bg-warning/10 dark:text-warning` + `info-circle`
  - warning: `bg-amber-100 text-amber-700 dark:bg-warning/10 dark:text-warning` + `alert-triangle`
  - danger: `bg-red-100 text-red-700 dark:bg-red-500/10 dark:text-red-400` + `alert-circle`
  - default: `bg-neutral-100 text-neutral-600 dark:bg-white/[0.06] dark:text-fg-dim` + `info-circle`
- Motion: `transition ease-out duration-200` in (`translate-y-2 opacity-0` →
  `translate-y-0 opacity-100`), `ease-in duration-150` out.
- Behavior: auto-dismiss **4000ms**, pause on hover, max **4 concurrent**,
  **no progress bar**; copy button (revealed on `group-hover`) + dismiss button
  (`size-7 rounded-md`, `aria-label="Dismiss"`).

### 5.6 Callout — `callout.blade.php`

- Root: `relative rounded-lg border px-3 py-2.5` + per-type shell:
  - warning: `border-warning/25 bg-warning/[0.07] dark:border-warning/20 dark:bg-warning/[0.06]`
  - danger: `border-red-300/60 bg-red-50 dark:border-red-500/20 dark:bg-red-500/[0.07]`
  - info: `border-coollabs/20 bg-coollabs/[0.055] dark:border-warning/15 dark:bg-warning/[0.045]`
  - success: `border-emerald-300/60 bg-emerald-50 dark:border-emerald-500/20 dark:bg-emerald-500/[0.07]`
- Icon `size-4 shrink-0 mt-0.5` + title `text-[12px] font-semibold` + body
  `mt-0.5 text-[12px] leading-5` (per-type color classes), dismiss button
  `size-7 rounded-md absolute top-1.5 right-1.5` with `aria-label="Dismiss"`.

### 5.7 Banner — `banner.blade.php`

- `relative z-999 w-full py-2 mx-auto duration-100 ease-out shadow-xs
  bg-coolgray-100 sm:py-0 sm:h-14`, slides down from `-translate-y-10`
  (`ease-out duration-200` in / `ease-in duration-100` out, 100ms delayed show).
- Close: `w-6 h-6 p-1.5 rounded-full text-neutral-200 hover:bg-coolgray-500`.

### 5.8 Popup — `popup.blade.php`

- Bottom-right slide-up card: `fixed bottom-0 right-0 w-full h-auto z-999`,
  panel `max-w-4xl p-6 mx-auto bg-white border shadow-lg lg:border-t
  dark:border-coolgray-300 border-neutral-200 dark:bg-coolgray-100 lg:p-8
  sm:rounded-sm`; `translate-y-full` → `translate-y-0` (`duration-500` in /
  `duration-300` out), 300ms delayed show.

### 5.9 Popup-small — `popup-small.blade.php`

- Corner warning card `fixed right-4 z-999 top-16|bottom-4`, panel
  `max-w-sm rounded-lg p-3 pr-10` + inline elevated/hairline/modal shadow;
  `translate-y-3 opacity-0` → `translate-y-0 opacity-100` (`duration-200`/
  `duration-150`). Minimize-to-icon affordance (icon `size-7 rounded-md
  bg-amber-100 text-amber-700 dark:bg-warning/10 dark:text-warning`).

### 5.10 Generic dropdown — `dropdown.blade.php`

- Panel `absolute top-full z-50 mt-1 min-w-max max-w-[calc(100vw-1rem)]`
  (inline variant: `w-full` + `shadow-sm dark:bg-coolgray-200`), enter
  `ease-out duration-200` from `-translate-y-2`. JS viewport positioning
  (`panelStyles` fixed on mobile).

### 5.11 Table dropdown — `table/dropdown.blade.php`

- Panel `listbox-panel fixed! top-auto! right-auto! bottom-auto! z-[90]! mt-0!`
  + `role="{{ $role }}"` (default `listbox`) + optional
  `aria-multiselectable="true"`; JS flips above when no room below.

### 5.12 Unsaved bar — `unsaved-bar.blade.php`

- Floating bottom-center pill: `pointer-events-none fixed inset-x-3
  bottom-[calc(var(--keyboard-inset,0px)+max(1.5rem,env(safe-area-inset-bottom,0px)+0.75rem))]
  z-[1000] flex max-w-full translate-y-6 scale-95 flex-col items-stretch gap-2
  rounded-2xl border border-neutral-200 bg-white py-2.5 pr-2.5 pl-4 opacity-0
  shadow-modal transition-[opacity,transform,scale] duration-300
  ease-[cubic-bezier(0.16,1,0.3,1)] … dark:border-white/10 dark:bg-surface`;
  `sm:left-1/2 sm:-translate-x-1/2 sm:w-max sm:flex-row`.
- State-driven via arbitrary variants `[&.is-dirty]:translate-y-0
  [&.is-dirty]:scale-100 [&.is-dirty]:opacity-100 [&.is-dirty]:delay-300` and
  `[&.is-saving]:…` (snap back `duration-200 ease-in`). Wired by
  `wire:dirty.class="is-dirty"` / `wire:loading.class="is-saving"`.
- Buttons: Reset (`h-8 rounded-lg bg-neutral-100 …`) and Save
  (`button-highlighted flex h-8 items-center gap-2 rounded-lg px-4 text-[13px]
  font-semibold active:scale-[0.98]`) with an Enter `<kbd>` hint.

### 5.13 Loading & empty states

- **`loading.blade.php`**: `inline-flex items-center justify-center gap-2
  text-[13px] text-neutral-500 dark:text-fg-dim` + `role="status"
  aria-live="polite"`; spinner `loading-indicator shrink-0 animate-spin`
  (`size-3` compact / `size-4`), circle `opacity-20` + arc `opacity-80`.
- **`page-loading.blade.php`**: `loading-indicator w-4 h-4 mx-1 ml-3
  animate-spin`.
- **`empty.blade.php`**: `empty-state flex w-full flex-col items-center
  justify-center rounded-xl border border-dashed border-neutral-300 px-6 py-10
  text-center dark:border-white/[0.1]` + min-height by size (`min-h-44` sm /
  `min-h-80` default / `min-h-96` lg). Icon badge `size-10/11/12 rounded-xl
  border bg-white text-neutral-400 shadow-sm dark:bg-white/[0.035]
  dark:text-fg-faint`; title `text-[14-15px] font-semibold text-black
  dark:text-fg`; description `mt-1 max-w-sm text-[12-13px] leading-5
  text-neutral-500 dark:text-fg-dim`; footer actions `mt-4 flex flex-wrap
  items-center justify-center gap-2`.
- **`checkpoint-item.blade.php`** — status row (`flex min-h-14 items-center
  gap-3 px-4 py-3`) with `size-8 rounded-lg border` icon badge:
  - success: `border-emerald-500/25 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400` + `check-circle`
  - error: `border-red-500/25 bg-red-500/10 text-red-600 dark:text-red-400` + `alert-circle`
  - running: `border-coollabs/25 bg-coollabs/10 text-coollabs dark:border-warning/25 dark:bg-warning/15 dark:text-warning` + spinner
  - pending: `border-neutral-200 text-neutral-400 dark:border-white/[0.1] dark:text-fg-faint` + dot
  - idle: `border-neutral-200 bg-neutral-50 text-neutral-500 dark:border-white/[0.08] dark:bg-white/[0.035] dark:text-fg-dim` + dot
  - Title `text-[13px] font-semibold`, description/slot `text-[11px]
    text-neutral-500 dark:text-fg-faint`.

### 5.14 Configuration warning — `configuration-warning.blade.php`

- Popover `role="dialog"`, `fixed top-14 left-1/2 z-[1100] w-[calc(100vw-2rem)]
  max-w-sm -translate-x-1/2 rounded-lg p-3 lg:absolute lg:top-full lg:right-0
  lg:left-auto lg:mt-2 lg:translate-x-0` + inline elevated/hairline/modal shadow.
  Trigger `h-8 rounded-lg px-2 text-amber-700 hover:bg-amber-100 dark:text-warning
  dark:hover:bg-warning/10` with `aria-haspopup="dialog" :aria-expanded`.

### 5.15 Legacy modal — `modal.blade.php`

- Native `<dialog class="modal">` with `modal-box` / `modal-backdrop` classes —
  **undefined in the repo's own CSS** (daisyUI is not a dependency). Treat as a
  deprecated shell; the canonical modal family is §5.3.

---

## 6. Layout & Navigation

Source: `resources/views/layouts/*.blade.php` and
`resources/views/components/{navbar,dashboard/navbar,settings/*,top-breadcrumb,top-user-menu,*}.blade.php`.

### 6.1 App shell — `layouts/app.blade.php`

Three-layer fixed stack:

1. **Desktop top bar**: `fixed top-0 inset-x-0 z-50 h-12 items-center bg-white/95
   dark:bg-panel/95 backdrop-blur` with a brand cell whose width animates
   `w-16`/`w-56` (`transition-[width] duration-200`).
2. **Desktop sidebar**: `hidden lg:fixed lg:top-12 lg:bottom-0 lg:left-0
   lg:z-40 lg:flex lg:flex-col min-w-0` with matching `lg:w-16`/`lg:w-56`.
3. **Layer-2 tab strip** (`components/dashboard/navbar.blade.php`):
   `lg:fixed lg:top-12 lg:right-0 lg:z-30 lg:h-12 … lg:left-16|lg:left-56 …
   lg:bg-white/95 lg:backdrop-blur` + a `hidden lg:block lg:h-12` spacer.

Main content pays both offsets: `lg:pt-[calc(3rem+1.75rem)]` and
`lg:ml-16`/`lg:ml-56`; width capped at `max-w-[1400px]` centered option.
The `calc(3rem + 1.75rem)` invariant (top bar `h-12` = 3rem + page padding
1.75rem) recurs as `scroll-margin-top: 7rem` on anchored cards.

**Mobile** (< `lg`): sticky top bar `sticky top-0 z-40 … px-4 py-3 sm:px-6
lg:hidden bg-white/95 dark:bg-panel/95 backdrop-blur-sm` + right-side slide-over
`relative z-[1000] lg:hidden` (`max-w-56`, `bg-black/80` overlay,
`role="dialog" aria-modal="true"`).

### 6.2 Sidebar navigation — `components/navbar.blade.php`

- `nav flex-col`, search, then `ul role=list -mx-1 flex min-h-0 flex-1 flex-col
  gap-y-0.5 overflow-y-auto px-1 pb-2 scrollbar`.
- Menu items use the `menu-item` utility family (§3.3); `menu-item-active` is a
  **solid neutral fill** (`bg-black/[0.05] dark:bg-white/[0.06]`) — deliberately
  no accent rail/border. Grouped under `nav-section` headers.
- Collapsible groups: `.nav-children` (app.css:111-116) = `position:relative;
  margin-left:1.1rem; padding-left:0.25rem; border-left:1px solid
  var(--color-hairline)` (vertical connector rail).
- Collapsed state at `lg` turns items into centered 2rem squares (§3.3).
- Sticky config sidebar `.application-settings-navigation` (app.css:1469-1493):
  `position:sticky; top:calc(3rem + 1.75rem); max-height:calc(100dvh - 5.5rem);
  padding-right:.375rem; overflow-x:hidden; overflow-y:auto;
  overscroll-behavior:contain; scrollbar-width:thin`; `top:4rem` inside the
  settings workspace; `.is-flush` → static.

### 6.3 Settings workspace — `components/settings/layout.blade.php`

- Shell: `grid min-w-0 gap-8 xl:grid-cols-[210px_minmax(0,1fr)]` — fixed 210px
  aside on `xl`, stacked below.
- Nav is a responsive grid: `grid-cols-2 sm:grid-cols-3 lg:grid-cols-4
  xl:grid-cols-1` (`components/settings/sidebar.blade.php`).
- Layer cards: `.application-settings-section` + `-header` + `-body`
  (§8.4); `.application-settings-form` scopes form label/input resets.

### 6.4 Breadcrumbs & user menu

- Top breadcrumb (`components/top-breadcrumb.blade.php`): `flex min-w-0
  items-center gap-0.5 text-[13px]` with `/` separators, `h-8` switcher pills,
  dropdown panels `listbox-panel scrollbar left-0! z-[90]!`, status pills `h-[22px]`.
- User menu (`components/top-user-menu.blade.php`): avatar pill `flex h-8 …
  rounded-full … shadow-sm`, panel `top-user-menu-panel listbox-panel z-[90]!
  w-52!` (flips `bottom-full!` above the sidebar footer on desktop).

### 6.5 Auth / boarding / error shells

- **Auth** (`components/auth/shell.blade.php`, CSS app.css:1063-1134):
  `auth-shell application-settings-form` → `auth-shell-content` → `auth-card`
  → `auth-card-heading` (h1 + p) → `auth-card-body` → `auth-card-footer`.
  `auth-card`: `width:min(100%,27rem); border-radius:10px;
  background:var(--coollabs-elevated); box-shadow:0 0 0 1px
  var(--coollabs-hairline), 0 20px 60px rgb(0 0 0 / .14)`. Body is a nested
  panel (`background:var(--coollabs-base)` + `box-shadow:0 0 0 1px
  var(--coollabs-fill)`); the ring creates the seam (no divider element).
  Shell background: `radial-gradient(circle at 50% 0%, color-mix(in oklab,
  var(--color-coollabs) 9%, transparent), transparent 34rem)` over canvas.
- **Error pages** (app.css:1188-1338): `.error-shell` 100% height flex-center,
  same radial gradient; `.error-code` = mono `clamp(3.5rem,12vw,5.5rem)` 600
  `-0.03em` accent color (purple light / yellow dark; `.error-code-danger` =
  `var(--color-error)` both themes); `.error-title` 1.25rem/600; description
  0.875rem `max-width:42ch`; `.error-message` code block = error-tinted
  `8%` background.
- **Boarding** (`layouts/boarding.blade.php`): `main.min-h-screen.flex
  items-center.justify-center.p-4`; stepper `grid grid-cols-3 overflow-hidden
  rounded-[10px] border … bg-white dark:bg-white/[0.025]` with `min-h-10` cells
  (`components/boarding-progress.blade.php`).

---

## 7. Data Display

Source: `resources/views/components/table/*.blade.php`,
`resources/views/components/{table-pagination,client-pagination,page-size-select,status-badge,status/*,resource-*,reicon,external-link,internal-link}.blade.php`.

### 7.1 Data tables

CSS-driven div-grids, not `<table>` elements (`app.css`):
- `.data-table-header` (app.css:2117): `display:grid; align-items:center;
  gap:1rem; padding:0 1rem; height:2.5rem; font-size:13px; font-weight:500;
  color:var(--coollabs-subtle); background:rgba(0,0,0,0.02);
  border-bottom:1px solid var(--coollabs-fill); border-radius:8px 8px 0 0`
  (dark: `rgba(255,255,255,0.02)`).
- `.data-table-row` (app.css:2143): `display:grid; align-items:center; gap:1rem;
  padding:0.625rem 1rem; min-height:3rem; transition:background-color .15s`;
  hover `rgba(0,0,0,0.02)` / `rgba(255,255,255,0.02)`.
- `.data-table-row-active` (app.css:1983): `background:var(--coollabs-fill);
  color:var(--coollabs-fg)`.
- Row separators in Blade: `border-b border-neutral-200 last:border-b-0
  dark:border-white/[0.07]`.
- **No row striping** (no `odd:`/`even:` anywhere) — flat rows + separators +
  hover tint. Column widths are per-table CSS grid templates
  (e.g. `.env-table-grid`, `.domains-table-grid`).

### 7.2 Table toolbar

- `table-toolbar flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center`;
  search wrapper `min-w-0 w-full flex-1 sm:max-w-md`; actions
  `flex flex-wrap items-center gap-2 sm:ml-auto`.
- **Search** (`table/search.blade.php`): `input w-full pl-8!` + leading search
  icon `size-3.5 text-neutral-400 dark:text-fg-faint` (replaced by spinner while
  loading) + clear button `absolute top-1/2 right-2 flex size-5 -translate-y-1/2
  items-center justify-center rounded text-neutral-400 hover:bg-neutral-100
  hover:text-black dark:hover:bg-white/[0.07]` (`aria-label="Clear search"`).
- **Filter** (`table/filter.blade.php`): trigger `button max-w-80 min-w-0`,
  `button-highlighted` when active filters; active-count pill
  `rounded-full bg-neutral-100 px-1.5 py-0.5 text-[10px] font-medium
  text-neutral-500 dark:bg-white/[0.07] dark:text-fg-dim`; reset footer strip
  `border-t border-neutral-200 bg-white p-1 dark:border-white/10 dark:bg-raised`.
- **Loading overlay** (`table/loading.blade.php`):
  `table-loading-overlay absolute inset-0 z-30 hidden items-center justify-center
  bg-white/70 backdrop-blur-[1px] dark:bg-black/20` + spinner scaled via
  `[&_.loading-indicator]:size-5`.

### 7.3 Pagination

- Footer: `flex min-h-11 items-center justify-between border-t border-neutral-200
  px-4 text-[11px] text-neutral-500 dark:border-white/[0.08] dark:text-fg-faint`.
- Summary: `inline-flex h-7 items-center whitespace-nowrap tabular-nums` —
  `{from}–{to} of {total}` (en dash).
- Pager buttons (shared class, Livewire + Alpine identical):
  `flex size-7 items-center justify-center rounded-md border border-neutral-200
  text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-black
  disabled:pointer-events-none disabled:opacity-35 dark:border-white/[0.08]
  dark:text-fg-dim dark:hover:bg-white/[0.06] dark:hover:text-fg` with
  `arrow-right` chevrons (`rotate-180` for previous), `aria-label="Previous page"`
  / `"Next page"`. **No numbered page buttons — prev/next only.**
- Loading: `loading-indicator size-3.5 animate-spin` + `<span class="sr-only">
  Loading page…</span>` inside `aria-live="polite"`.
- Page-size selector (`page-size-select.blade.php`): compact trigger
  `inline-flex h-7! w-12! items-center justify-between border-0 px-1 text-[11px]!
  leading-none! tabular-nums …` + `listbox-option` panel + custom numeric input
  (`h-7! w-14! text-[11px]! tabular-nums`).

### 7.4 Status badges

Universal pill (`status-badge.blade.php`) base:
`inline-flex h-6 max-w-full items-center gap-1.5 whitespace-nowrap rounded-full
border border-neutral-200 bg-neutral-100 px-2 text-xs font-medium leading-none
text-neutral-700 dark:border-white/[0.12] dark:bg-white/[0.07] dark:text-white`.
Dot `size-1.5 shrink-0 rounded-full` + color map:
- `neutral` → `bg-neutral-400 dark:bg-neutral-500` (stopped)
- `success` → `bg-emerald-500` (running)
- `warning` → `bg-warning` (restarting, degraded)
- `error` → `bg-red-500`

Refresh badge adds `min-w-[4.5rem] justify-center cursor-pointer border-transparent
hover:bg-neutral-200 disabled:cursor-wait disabled:opacity-70 dark:hover:bg-coolgray-300`
+ `aria-label="Refresh status"`. Misc pills: deprecated →
`bg-warning/15 text-warning border-warning/30 rounded-full px-2 py-0.5 text-xs`;
two-factor → `text-green-600 dark:text-green-400` / muted shield icon + `sr-only`.

### 7.5 Resource tabs & cards

- Tab scroller (`resource-heading-tabs.blade.php`): track
  `resource-heading-tabs flex w-full min-w-0 items-center gap-0.5 overflow-x-auto`
  (scrollbar hidden via `scrollbar-width:none` at app.css:1588-1597); circular
  scroll controls `.resource-heading-tabs-control-icon` = 24px white disc with
  `box-shadow:0 1px 2px rgba(0,0,0,.06), 0 0 0 1px rgba(0,0,0,.08)` (dark: raised
  bg + white/10 ring); active detected via `aria-current="page"` /
  `data-active` / accent-containing classes.
- Overflow menu (`resource-heading-overflow.blade.php`): trigger
  `button resource-heading-overflow-trigger` with `play-circle` icon; collapsed
  panel reuses listbox: `listbox-panel top-full! right-0! left-auto! mt-1!
  min-w-52!` with `role="menu"`.
- List card (`resource-view.blade.php`): `group flex min-w-0 items-center gap-3
  rounded-[10px] border border-neutral-200 bg-white p-3 transition-…
  dark:border-white/[0.07] dark:bg-surface`; hover
  `hover:border-neutral-300 hover:bg-neutral-50 hover:shadow-sm
  dark:hover:border-white/[0.12] dark:hover:bg-white/[0.035]`; locked state
  `cursor-not-allowed opacity-60`. Logo tile `size-10 rounded-lg bg-neutral-100
  dark:bg-white/[0.06]`; title `truncate text-sm font-semibold text-black
  dark:text-fg`; sub-line `mt-0.5 line-clamp-2 text-xs leading-5 text-neutral-500
  dark:text-fg-dim`.

### 7.6 Icons — `reicon.blade.php`

- Wrapper: `<svg {{ $attributes->merge(['class' => 'size-4']) }} viewBox="0 0 24
  24" fill="none" xmlns="…" aria-hidden="true">` — **default size `size-4`
  (16px)**, callers override with `size-3`…`size-6`.
- All glyphs `currentColor`; stroke glyphs `stroke-width="1.5"` with
  round caps/joins; fill glyphs `fill="currentColor"`. Scaled groups use
  `transform="scale(1.33333)"` (chevron-down, unordered-list, file-content) or
  `scale(0.09375)` (Phosphor-style broom, shield-star, network).
- Catalog (69 names): fire, cloud, code, mail, dashboard, projects, servers,
  sources, destinations, storages, variables, notifications, keys, tags,
  time-back, terminal, profile, teams, subscription, settings, admin, sponsor,
  documentation, feedback, logout, search, plus, grid, eye, eye-off, eye-off2,
  globe, browser-terminal, sliders, filter, sort-direction, refresh, refresh3,
  restart, stop, stop-circle, play-circle, browser-code, database, layers,
  unordered-list, file, file-content, folder, alert-triangle, alert-circle,
  check-circle, info-circle, arrow-right, upload, x, check, chevron-down, trash,
  external-link, server-update, calendar, cpu, graph, shield-alert, bandage,
  broom, shield-star, network.

### 7.7 Link components

- `external-link.blade.php`: `inline-flex w-3 h-3 dark:text-neutral-400
  text-black`, stroke-width 2 arrow-out-of-box.
- `internal-link.blade.php`: `inline-flex w-4 h-4 text-black dark:text-white`,
  right-arrow `M5 12h14m-6 6l6-6m-6-6l6 6`.
- CSS link classes: `.auth-text-link` (app.css:1136) 0.8125rem/500, hover accent;
  `.error-contact-link` (app.css:1319) `inline-flex gap:.25rem`, hover accent +
  underline. Text-link convention elsewhere: `underline dark:text-warning`.

---

## 8. Layer-Card Anatomy (`.application-settings-section`)

The dominant card idiom — **elevated shell, hairline ring, nested base body,
fill ring** (app.css:1342-1460, 2066-2075):

- Section: `display:flex; flex-direction:column; border-radius:8px;
  background:var(--coollabs-elevated); box-shadow:0 0 0 1px
  var(--coollabs-hairline); scroll-margin-top:7rem`.
- Header: `min-height:3rem; flex-wrap; align-items:center;
  justify-content:space-between; gap:.5rem; padding:.5rem .5rem .5rem 1rem;
  border-radius:8px 8px 0 0; font-weight:500; color:var(--coollabs-subtle)`;
  `h2,h3` = `0.875rem / 500 / 1.25rem`.
- Body: `border-radius:8px; background:var(--coollabs-base); box-shadow:0 0 0
  1px var(--coollabs-fill); padding:1rem`.
- `is-flush` (app.css:2066): `padding:0` (full-bleed tables).
- `is-section-highlight::after` (app.css:1378): 0.5px accent border + 500ms fade
  ring animation.
- **This shell is reused verbatim by every modern modal** (§5.3), the auth card
  (§6.5), boarding steps, and settings sections.

---

## 9. Terminal / Console Surfaces

- Log canvas `--color-log: #0d0d0d`; fonts `--font-logs` (mono).
- `coolify-monaco-editor` shell: radius 10px, 1px `--coollabs-line` border
  (app.css:271-281). Custom `coolify-dark` Monaco theme (§4.13).
- Terminal theme selector (`terminal/theme-selector.blade.php`): trigger
  `terminal-theme-trigger flex h-8 items-center gap-2 rounded-md px-2.5 text-xs
  font-medium text-white/70 hover:bg-white/[0.08] hover:text-white` (white-on-
  console styling); panel `console-theme-selector absolute top-11 right-0 z-50
  max-h-80 w-56 overflow-y-auto rounded-lg border border-neutral-200 bg-white
  p-1 shadow-[0_18px_50px_rgba(0,0,0,0.18)] dark:border-white/[0.1]
  dark:bg-[#111113] dark:shadow-[0_18px_50px_rgba(0,0,0,0.55)]`; swatch rows
  `flex h-8 w-full items-center gap-2 rounded-md px-2 text-left text-[11px]`.
- Mobile terminal key rows: `.terminal-mobile-key` / `.terminal-key-row`
  (app.css:80-88) — translucent white borders via
  `color-mix(in srgb, var(--terminal-scrollbar, #fff) 22-24%, transparent)`.
- Log line rendering: `content-visibility:auto` + per-level background tints
  (`log-line`, `log-error`, `log-warning`, `log-debug`, `log-info`).

---

## 10. Motion System

- **No tw-animate-css utility usage in the component layer** — `tw-animate-css`
  is imported (`app.css:4`) but the 22 overlay components use Alpine
  `x-transition` + Tailwind `transition-*` classes exclusively. Only
  `animate-spin` is used for spinners.
- **Modal family** (modal-confirmation, modal-input, domain-conflict): enter
  `ease-out duration-100`, leave `ease-in duration-100`, translate/scale combo
  `opacity-0 -translate-y-2 sm:scale-95`.
- **Process dialog**: `duration-150` in, `duration-100` out, enters **from
  below** (`translate-y-2`).
- **Slide-over**: `transform transition ease-in-out duration-100 sm:duration-300`
  with `translate-x-full`.
- **Toast**: `ease-out duration-200` in, `ease-in duration-150` out.
- **Popup**: `duration-500` in / `duration-300` out, `translate-y-full`.
- **Popup-small**: `duration-200` in / `duration-150` out, `translate-y-3`.
- **Banner**: `duration-200` in / `duration-100` out, `-translate-y-10`.
- **Dropdown**: `ease-out duration-200` from `-translate-y-2`.
- **Unsaved-bar**: `duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]` with
  `translate-y-6 scale-95` → `translate-y-0 scale-100` (+ 300ms delay when
  dirty); saves snap back at `duration-200 ease-in`.
- **Listbox panel**: `ease-out duration-100` with `-translate-y-1 scale-[0.98]`.
- **Helper popover**: `ease-out duration-100` / `ease-in duration-75`,
  `translate-y-0.5`.
- Spinners: `animate-spin` + `loading-indicator` (`text-coollabs
  dark:text-warning`); dark-mode override turns all spinners yellow
  (`app.css:377-379`).

---

## 11. Accessibility Patterns

- **Focus language**: inputs/selects use accent border + 1px shadow
  (§3.2); checkbox uses `peer-focus-visible:ring-2 ring-coollabs/25 ring-offset-2`;
  compact/icon buttons use `focus-visible:ring-1 focus-visible:ring-accent`;
  slide-over close uses `ring-2` + offset. All dark variants swap to
  `ring-warning` + `ring-offset-base`.
- **ARIA inventory** (cross-cutting, verified across table, pagination, tabs,
  modal, toast, loading components):
  - `aria-current="page"` on active tabs;
  - `aria-expanded` on dropdown/filter/sort/page-size/theme/overflow triggers;
  - `aria-haspopup="listbox"|"menu"|"dialog"` on the matching triggers;
  - `role="listbox"` + `aria-multiselectable="true"` on multiselect panels,
    `role="option"` + `:aria-selected` on options, `role="menu"` on collapsed
    overflow, `role="status"` + `aria-live="polite"` on loading,
    `role="dialog"` + `aria-modal="true"` + `aria-labelledby` on process-dialog;
  - `aria-label` on icon-only buttons (search, clear, pagination, refresh,
    scroll tabs, theme, dismiss, restore/minimize);
  - `aria-hidden="true"` on all decorative reicon SVGs, spinners, scroll
    controls, mobile nav clones;
  - `sr-only` for status text and pagination loading; `title` tooltips on badges;
  - `rel="noopener noreferrer"` on external links.
- **Focus traps**: `x-trap.inert.noscroll` on every modern modal
  (modal-confirmation, modal-input, process-dialog, domain-conflict-modal).
- **Escape-to-close**: modal-confirmation, modal-input, slide-over, process-dialog
  (unless `closeWithX`), domain-conflict-modal, table/dropdown,
  configuration-warning.
- **Autofocus**: modal-input focuses the first `input, textarea, select` on open.
- **Global icon tooltip** converts `title` → `aria-label` and removes the `title`
  (`icon-tooltip.blade.php`) — icon-only buttons keep accessible names.
- **Helper popovers** use `role="tooltip"` + `aria-describedby` wiring
  (`helper.blade.php`).

---

## 12. Responsive Behavior

- **Breakpoints**: standard Tailwind `sm (640) / md (768) / lg (1024) / xl (1280)`.
- **Shell**: desktop top-bar + sidebar + layer-2 tab strip appear only at `lg`;
  below `lg` a sticky mobile top bar + right slide-over drawer take over (§6.1).
- **Sidebar collapse**: at `lg` the sidebar can collapse to 2rem-square icons
  (w-16) with widths animating between `w-16`/`w-56`; menu labels hide via
  `.sidebar-collapsed-label` (utilities.css:407-422).
- **Settings workspace**: `grid-cols-2 sm:grid-cols-3 lg:grid-cols-4
  xl:grid-cols-1` nav grid; aside becomes a fixed column only at `xl`.
- **Domain input**: 3-column grid only at `sm` (protocol/host/port), stacks below.
- **Toolbars**: table toolbar stacks on mobile, wraps on `sm`, actions
  right-align via `sm:ml-auto`.
- **Tables**: header 2.5rem / rows min-3rem with `gap-1rem`; per-table grid
  templates; no horizontal scroll wrapper is part of the component (handled by
  layout).
- **Modals**: centered with `p-4` on mobile (`items-start`), `sm:items-center`;
  mobile scale animation disabled (`sm:scale-95` only).
- **Toast/popup-small**: full-width minus 2rem on mobile
  (`w-[calc(100%-2rem)]` / `w-[calc(100vw-2rem)]`), capped at `sm:max-w-[26rem]`
  / `max-w-sm`.
- **Mobile input zoom**: all inputs forced to 16px on `max-width: 767px`
  (app.css:247-253).
- **Breadcrumb switcher pills** are `h-8`; status pills `h-[22px]`; version chip
  `text-[10.5px]` in top bars.

---

## 13. Adoption Checklist

To port this system into another Tailwind v4 project:

1. Copy the `@theme` token block (§2.1–2.3, `app.css:17-68`) and the
   `--coollabs-*` ladder (§2.4, `app.css:924-992`).
2. Add `@custom-variant dark (&:where(.dark, .dark *))` (app.css:15) and the
   `color-scheme` rules (app.css:119-127).
3. Copy `utilities.css` wholesale (§3) — it is self-contained `@utility` blocks.
4. Port the unlayered component CSS from `app.css`: listbox family
   (1872-2063), chips (3526-3614), app-tab scoping (1761-1838), layer cards
   (1342-1460, 2066-2075), data tables (1983, 2117-2143), nav rail (111-116),
   sticky sidebar (1469-1493), auth/error shells (1063-1134, 1188-1338),
   button attribute variants (287-293), monaco shell (271-281),
   coolbox loading (138-246).
5. Port the Blade components you need (forms §4, overlays §5, layout §6,
   data display §7) — all class strings in this document are verbatim from the
   repo and can be adopted as-is, or reimplemented in React/Vue/plain HTML
   since the system is Tailwind-only.
6. Respect the invariants: 32px control rows, 13px UI text, hairline rings
   instead of heavy borders, solid neutral active fills (no accent rails),
   the purple-light/yellow-dark accent duality, and the dirty-state
   inset-bar pattern.
