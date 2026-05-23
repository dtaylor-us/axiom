# Archon UI — UX Style Guide

This document is the single authoritative reference for all visual and interaction decisions in the Archon frontend. Every new component, view, or UI change must comply with this guide. When in doubt, check what an equivalent element looks like in an existing view before inventing a new pattern.

---

## Design principles

1. **Density over decoration.** The application renders complex, information-dense output. Every pixel of decoration that does not convey meaning is a pixel of signal lost.
2. **Consistency over creativity.** Use the tokens and patterns defined here. Do not invent new colours, radii, or spacing values unless they are missing from this guide entirely.
3. **Motion is intentional.** The only acceptable entrance animation is `.archon-reveal`. Do not add CSS transitions, keyframe animations, or Framer Motion to elements unless explicitly listed here.
4. **Accessibility is not optional.** All interactive elements must have visible focus rings, all icons must carry `aria-hidden="true"` or descriptive `aria-label`, all images and diagrams must have `alt` text.

---

## CSS custom properties / theme tokens

Defined in `src/index.css` via `@theme {}`. Use these Tailwind utilities, never raw hex values.

| Utility | Value | When to use |
|---------|-------|-------------|
| `bg-sidebar` | `#202123` | Sidebar background |
| `bg-sidebar-hover` / `hover:bg-sidebar-hover` | `#2A2B32` | Sidebar hover state, active nav item |
| `border-sidebar-border` | `#4E4F60` | Sidebar borders and dividers |
| `bg-accent` | `#10a37f` | Primary action buttons, active indicator dots, spinners |
| `bg-accent-hover` / `hover:bg-accent-hover` | `#0d8c6d` | Primary button hover |
| `text-accent` | — | Accent-coloured text and SVG strokes |
| `focus:ring-accent` | — | Focus ring on interactive elements |

> **Rule:** Never write `bg-[#10a37f]` or `text-[#202123]` inline. Always use the semantic token.

---

## Colour system

### Semantic surface colours

| Surface | Classes |
|---------|---------|
| Page background | `bg-gray-50` |
| Card / panel | `bg-white border border-gray-200` |
| Sidebar | `bg-sidebar` |
| Active session panel in sidebar | `bg-sidebar-hover/30 border border-sidebar-border` |
| Highlighted row / accent tint | `bg-accent/5` or `bg-accent/10` |

### Text colours

| Role | Class |
|------|-------|
| Primary heading | `text-gray-900` |
| Secondary heading | `text-gray-800` |
| Body / description | `text-gray-600` |
| Muted / meta | `text-gray-500` |
| Disabled / placeholder | `text-gray-400` |
| Sidebar primary text | `text-white` (active) / `text-gray-200` (hover) |
| Sidebar secondary text | `text-gray-400` |
| Monospace / badge labels | `text-gray-500` |

### Semantic status colours (badges, icons, rows)

| Semantic role | Background | Text / stroke |
|---------------|-----------|---------------|
| Complete / success | — | `text-emerald-400` |
| Running / in-progress | `bg-accent/10` row | `text-accent animate-spin` icon |
| Error | — | `text-red-400` |
| Aborted | — | `text-gray-500` |
| Pending | — | `text-gray-600` |

### Alert / banner colours (always `rounded-xl` + border + icon)

| Type | Container | Heading text | Body text | Border |
|------|-----------|-------------|-----------|--------|
| Warning | `bg-amber-50` | `text-amber-900 font-semibold` | `text-amber-800` | `border-amber-200` |
| Error | `bg-red-50` | `text-red-800 font-semibold` | `text-red-700` | `border-red-100` |
| Info / blockquote | `bg-blue-50/40` | — | `text-gray-600` | `border-l-4 border-blue-400/50` |

### Badge colours (severity / priority)

Badges use `rounded-full px-2.5 py-1 text-[11px] font-semibold`. Pick the semantic pair:

| Level | Classes |
|-------|---------|
| Critical / high severity | `bg-red-100 text-red-700` |
| High effort / warning | `bg-orange-100 text-orange-700` |
| Medium / caution | `bg-yellow-100 text-yellow-700` |
| Low / ok | `bg-green-100 text-green-700` |
| Medium effort / info | `bg-blue-100 text-blue-700` |
| Neutral / optional | `bg-gray-100 text-gray-600` |
| Governance / review | `bg-emerald-50 text-emerald-700` |

### FMEA RPN colour scale (applied to table cells)

| RPN range | Classes |
|-----------|---------|
| ≥ 200 | `bg-red-600 text-white` |
| 100–199 | `bg-orange-500 text-white` |
| 50–99 | `bg-yellow-400 text-gray-900` |
| < 50 | `bg-green-400 text-gray-900` |

---

## Typography

**Font stack:** `'Söhne', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif`  
Set globally on `body`. Do not change the font stack per component.

**Anti-aliasing:** `-webkit-font-smoothing: antialiased` — set globally.

### Scale

| Role | Tailwind classes |
|------|-----------------|
| Hero heading | `text-3xl font-semibold text-gray-900 tracking-tight` |
| Page / section heading | `text-2xl md:text-3xl font-semibold text-gray-900` |
| Section title (with icon) | `text-lg font-bold text-gray-900` |
| Card / panel title | `text-sm font-semibold text-gray-800` |
| Subtitle (below heading) | `text-base font-medium text-gray-500 mt-1 tracking-wide` |
| Body — long form | `text-[15px] text-gray-600 leading-relaxed` |
| Body — compact | `text-sm text-gray-600 leading-relaxed` |
| Body — tight | `text-xs text-gray-600` |
| Sidebar nav item | `text-[13px]` |
| History / meta list item | `text-[12px]` |
| Badge / label / tag | `text-[11px] font-semibold` |
| Uppercase section label | `text-[10px] font-semibold text-gray-500 uppercase tracking-widest` |
| Monospace ID / code inline | `font-mono text-[12px] text-gray-500` |

### Markdown rendered headings (`MarkdownRenderer.tsx`)

| Level | Classes |
|-------|---------|
| h2 | `text-lg font-bold text-gray-800 mt-8 mb-3 pb-1.5 border-b border-gray-200 first:mt-0` |
| h3 | `text-base font-semibold text-gray-800 mt-6 mb-2` |
| h4 | `text-sm font-semibold text-gray-700 mt-4 mb-1` |

---

## Spacing and layout

### Content widths

| Context | Max width |
|---------|-----------|
| Chat message thread | `max-w-3xl mx-auto w-full` |
| Home / landing page | `max-w-5xl mx-auto` |
| Card grids within a two-column layout | Natural grid columns |

### Page padding

| Breakpoint | Padding |
|-----------|---------|
| Mobile | `p-6` |
| Desktop (`md:`) | `p-10` |

### Gap and spacing conventions

| Context | Value |
|---------|-------|
| Between major sections | `mt-10`, `space-y-8` |
| Between cards in a grid | `gap-8` (major), `gap-3` (minor card grid) |
| Icon-to-label gap in buttons and nav | `gap-2` or `gap-2.5` |
| Intra-card spacing | `space-y-4` |
| Badge / inline gap | `gap-1.5` |

---

## App shell

The shell is a two-panel layout:

```
┌────────────────────────────┬──────────────────────────────────────┐
│  Sidebar (280px, hidden    │  Main content area (flex-1, p-6)     │
│  below md breakpoint)      │                                      │
│  bg-sidebar                │  View renders here                   │
└────────────────────────────┴──────────────────────────────────────┘
```

- Shell root: `flex h-full`
- Sidebar: `hidden md:flex w-[280px] shrink-0 bg-sidebar flex-col`
- Main: `flex-1 min-w-0 overflow-hidden`

---

## Sidebar

### Structure (top → bottom)

1. **New chat button** — `border border-sidebar-border rounded-lg px-3 py-2.5 text-[13px] text-gray-200 hover:bg-sidebar-hover transition-colors`
2. **Primary nav** (Home, Chat) — icon + label, `text-[13px]`
3. **Active session panel** (conditional) — `rounded-lg border border-sidebar-border bg-sidebar-hover/30`, contains Architecture and Governance nav items
4. **History list** — overflow scroll with custom scrollbar via `.sidebar-scroll`
5. **User / logout row** — bottom, `mt-auto`

### Nav item states

| State | Classes |
|-------|---------|
| Active | `bg-sidebar-hover text-white` |
| Inactive | `text-gray-400 hover:bg-sidebar-hover hover:text-gray-200` |

### Active session indicator (dot)

```tsx
<span className="inline-block w-1.5 h-1.5 rounded-full bg-accent shrink-0" />
```

### History item — active session

```
bg-accent/15 text-white ring-1 ring-accent/40 rounded-lg
```

---

## Buttons

### Primary (CTA)

```tsx
className="inline-flex items-center justify-center gap-2 rounded-lg bg-accent text-white
           px-4 py-2.5 text-sm font-semibold
           hover:bg-accent-hover
           focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2
           transition-colors
           disabled:opacity-40"
```

Always: `disabled:opacity-40`, `transition-colors`, a visible focus ring.

### Small action button (in banners, toolbars)

```tsx
className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600 text-white
           px-3 py-1.5 text-xs font-semibold
           hover:bg-amber-700 transition-colors"
```

Adjust the colour to match the semantic context (amber for warning, red for destructive, accent green for default).

### Ghost / sidebar button

```tsx
className="flex items-center gap-2 w-full border border-sidebar-border rounded-lg
           px-3 py-2.5 text-[13px] text-gray-200
           hover:bg-sidebar-hover transition-colors
           disabled:opacity-40"
```

### Icon-only button

Wrap in a `<button>` with `aria-label` and `title`. Use `rounded-md p-1 hover:bg-gray-100 transition-colors text-gray-500 hover:text-gray-700` or equivalent.

### Rules for all buttons

- Always `transition-colors`
- Always `disabled:opacity-40` when disabling is a valid state
- Always `focus:outline-none` paired with a custom `focus:ring-*`
- Never use `cursor-pointer` on a `<button>` — it is the default. Do use `cursor-not-allowed` on disabled states when the element looks interactive (e.g. history items disabled during streaming)

---

## Form inputs

All inputs share a base pattern:

```tsx
className="w-full border border-gray-200 rounded-lg px-3 py-2.5
           text-sm text-gray-800 placeholder:text-gray-400
           focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent
           transition-colors"
```

**Labels:**

```tsx
<label className="block text-xs font-medium text-gray-600 mb-1">
```

**Error state:** add `border-red-300 focus:border-red-500 focus:ring-red-500` to the input.

**Textarea (chat input):** same base, plus `resize-none overflow-hidden` and auto-height via JS.

---

## Cards

### Standard content card

```tsx
className="rounded-xl border border-gray-200 bg-white p-4"
```

### Card with accent tint (e.g., governance stage highlight)

```tsx
className="rounded-xl border border-gray-200 bg-accent/5 p-4"
```

### Login / form card

```tsx
className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6"
```

Use `rounded-2xl` and `shadow-sm` only for elevated modal-like cards (login, onboarding). All other cards use `rounded-xl` with no shadow — rely on the border.

---

## Logo / brand icon

Used consistently across Login, Home, and Chat empty state:

```tsx
<div className="w-14 h-14 mx-auto bg-accent/90 rounded-2xl flex items-center justify-center shadow-sm">
  <svg className="w-7 h-7 text-white" viewBox="0 0 24 24" fill="none"
       stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 21h18M3 10h18M12 3l9 7H3l9-7zM5 10v11m4-11v11m4-11v11m4-11v11" />
  </svg>
</div>
```

Smaller variant (in sidebar nav, home header): `w-12 h-12` container, `w-6 h-6` SVG.  
In a `ring-1 ring-accent/30` variant: add that class to the container when it appears in the chat empty state over a white field.

---

## Icons

All icons are inline SVG. No icon font, no external icon library.

### Standard attributes

```tsx
<svg
  className="w-4 h-4"             // use size classes from the table below
  viewBox="0 0 24 24"             // or 0 0 16 16 for 16-grid icons
  fill="none"
  stroke="currentColor"
  strokeWidth="1.5"               // 1.5 for outline; 2 for bolder action icons; 2.5 for status icons
  strokeLinecap="round"
  strokeLinejoin="round"
  aria-hidden="true"              // always on decorative icons
>
```

### Size scale

| Context | Size |
|---------|------|
| Sub-label / inline status | `w-3.5 h-3.5` |
| Standard UI icon | `w-4 h-4` |
| Button icon (with label) | `w-4 h-4` |
| Section / heading icon | `w-4 h-4` |
| Hero / branding icon | `w-6 h-6` or `w-7 h-7` |

### Colour

- Decorative / structural: `text-gray-700` or `currentColor` (inherits from parent)
- Status: use semantic status colours above
- Sidebar: `text-gray-400` (inactive) / `text-gray-200` (hover) / `text-white` (active)
- Error icons: `text-red-500`
- Warning icons: `text-amber-600`

---

## Animations and motion

### `.archon-reveal` — entrance animation

Single-use entrance fade-up, defined in `index.css`:

```css
@keyframes archon-reveal {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}
.archon-reveal {
  animation: archon-reveal 500ms ease-out both;
  animation-delay: var(--reveal-delay, 0ms);
}
```

Usage:

```tsx
<section
  className="archon-reveal"
  style={{ ['--reveal-delay' as any]: '80ms' }}
>
```

**Use on:** top-level sections within static views (Home). Stagger siblings in increments of ~60ms.

**Do not use on:** dynamically inserted content (chat messages), loading states, error banners, or anything that appears as a result of a user action — only on view-level content that is present on first render.

**Reduced motion:** automatically disabled by the media query in `index.css`.

### Spinner (loading)

```tsx
<svg className="w-4 h-4 animate-spin text-accent shrink-0" viewBox="0 0 16 16"
     fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
  <circle cx="8" cy="8" r="6" strokeOpacity="0.25" />
  <path d="M8 2a6 6 0 0 1 6 6" />
</svg>
```

Use this exact SVG. Do not use Tailwind's built-in `animate-spin` on a `div` border trick.

### Transitions

All interactive elements that change colour on hover use `transition-colors`. No other Tailwind transition class is used in the codebase.

---

## Tabs (GovernanceView pattern)

The tab bar renders inside the view, not in the sidebar. Pattern:

```tsx
<div className="flex gap-1 border-b border-gray-200 mb-6">
  {tabs.map((tab) => (
    <button
      key={tab.key}
      onClick={() => setActiveTab(tab.key)}
      className={`px-3 py-2 text-sm font-medium transition-colors border-b-2 -mb-px
        ${activeTab === tab.key
          ? 'border-accent text-accent'
          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}
    >
      {tab.label}
    </button>
  ))}
</div>
```

---

## Alert banners

All banners follow this slot structure: icon left, content block, optional action button right.

```tsx
<div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 flex items-start gap-3">
  {/* Icon — always w-4 h-4 shrink-0 mt-0.5 */}
  <svg className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" .../>
  <div className="min-w-0 flex-1">
    <p className="text-sm font-semibold text-amber-900">Title</p>
    <p className="text-sm text-amber-800 mt-1">Body</p>
  </div>
  {/* Optional action */}
  <button className="shrink-0 inline-flex items-center gap-1.5 rounded-lg bg-amber-600
                     text-white px-3 py-1.5 text-xs font-semibold hover:bg-amber-700 transition-colors">
    Action
  </button>
</div>
```

Swap amber → red for error banners.

---

## Tables

All data tables rendered in views follow the pattern from `MarkdownRenderer.tsx`:

```tsx
<div className="overflow-x-auto my-4 rounded-lg border border-gray-200">
  <table className="min-w-full divide-y divide-gray-200 text-sm">
    <thead className="bg-gray-50">
      <tr>
        <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">
          Column
        </th>
      </tr>
    </thead>
    <tbody>
      <tr className="border-t border-gray-100 even:bg-gray-50/50">
        <td className="px-3 py-2 text-gray-700 align-top">Value</td>
      </tr>
    </tbody>
  </table>
</div>
```

**FMEA / SeverityGrid tables** deviate slightly (no rounded container border, colour-coded cells) — follow the pattern in `SeverityGrid.tsx` for those.

---

## Loading and empty states

### Full-view loading

```tsx
<div className="p-6 flex items-center gap-2 text-gray-500">
  {/* spinner SVG */}
  Loading architecture…
</div>
```

### Error state (full-view)

```tsx
<div className="p-6">
  <div className="bg-red-50 border border-red-100 rounded-xl px-4 py-3">
    <p className="text-sm font-semibold text-red-800">Unable to load architecture</p>
    <p className="text-sm text-red-700 mt-1">{error}</p>
  </div>
</div>
```

### Empty / no data state (inline)

```tsx
<p className="text-gray-400 italic">No content available</p>
```

---

## Stage progress (StageProgress component)

Each stage row:

```tsx
className={`flex items-center gap-2 px-3 py-1 rounded-md text-[12px] transition-colors
  ${rowTextColor(status)}
  ${status === 'running' ? 'bg-accent/10' : ''}`}
```

`StatusIcon` sub-component: `w-3.5 h-3.5 shrink-0` with semantic colour.

Do not alter this component's render without also updating `STAGE_LABELS` and the test assertions (see RULE T-7 in copilot-instructions.md).

---

## Background grid (chat empty state)

The radial dot grid used in the chat welcome screen:

```tsx
<div className="pointer-events-none absolute inset-0" aria-hidden="true">
  <div className="absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(16,163,127,0.14)_1px,transparent_1px)]
                  [background-size:18px_18px] opacity-35" />
  <div className="absolute inset-0 bg-gradient-to-b from-white via-white to-gray-50" />
</div>
```

Use this exact pattern and only in the chat empty state. Do not apply it to other views.

---

## Scrollbars

The sidebar has a custom scrollbar applied via `.sidebar-scroll` in `index.css`:

```css
.sidebar-scroll::-webkit-scrollbar { width: 6px; }
.sidebar-scroll::-webkit-scrollbar-thumb { background: #4e4f60; border-radius: 3px; }
.sidebar-scroll::-webkit-scrollbar-track { background: transparent; }
```

Apply `sidebar-scroll` only inside the sidebar. All other scrollable regions use the browser default.

---

## Responsive breakpoints

The app uses three meaningful layouts:

| Breakpoint | Description |
|-----------|-------------|
| `< md` (< 768px) | Mobile — no sidebar, mobile drawer instead |
| `md` (≥ 768px) | Desktop — sidebar visible |
| `lg` (≥ 1024px) | Wide desktop — two-column grids on HomeView |

Classes used: `hidden md:flex`, `grid-cols-1 lg:grid-cols-2`, `max-w-5xl`, `p-6 md:p-10`.

---

## Accessibility

- All `<button>` elements must have either visible label text or an `aria-label`.
- All decorative SVG icons: `aria-hidden="true"`.
- Semantic SVG icons (conveying unique info): remove `aria-hidden`, add `role="img"` and `aria-label`.
- Landmark elements: `<nav>`, `<main>`, `<aside>`, `<header>`, `<section aria-labelledby>` are used in existing views — continue this pattern.
- All interactive elements must have visible focus styling — never use `focus:outline-none` without pairing it with `focus:ring-*`.
- `<ol>` / `<ul>` for lists of items, `<li>` for each item. Do not use `<div>` stacks to simulate lists.
- Screen reader text for icon-only status: use `<span className="sr-only">`.

---

## `data-testid` conventions

All interactive and significant structural elements carry a `data-testid` attribute for test targeting.

| Pattern | Example |
|---------|---------|
| View root | `data-testid="home-view"`, `"chat-view"`, `"governance-view"` |
| Major interactive elements | `data-testid="home-start-session"`, `"new-chat"` |
| Nav items | `data-testid="nav-home"`, `"nav-chat"`, etc. |
| Stage rows | `data-testid="stage-{name}"` |
| Loading/error/empty states | `data-testid="governance-loading"`, `"governance-error"` |
| Form fields | `data-testid="auth-email"`, `"auth-password"`, `"auth-error"` |

The `data-testid` attribute must be the **last** attribute on the element. Do not use arbitrary string IDs — follow the naming conventions above.

---

## Do / Do not at a glance

| ✅ Do | ❌ Do not |
|------|----------|
| Use semantic token classes (`bg-accent`, `bg-sidebar`) | Write raw hex values in class strings |
| Use `rounded-xl` for cards, `rounded-2xl` for hero icons | Mix radius values arbitrarily |
| Use `transition-colors` on all hover-interactive elements | Add `transition-all` or `duration-300` unless there is a measured reason |
| Add `aria-hidden="true"` to all decorative SVGs | Leave SVGs without accessibility attributes |
| Use `disabled:opacity-40` on disabled buttons | Use `opacity-50` or `opacity-30` for different values |
| Use `.archon-reveal` only on view-level static content | Apply entrance animation to dynamically inserted content |
| Use `text-[13px]` for sidebar nav, `text-[12px]` for history | Use `text-sm` (`14px`) in sidebar contexts |
| Keep all icons inline SVG with `fill="none"` | Import icon libraries or use emoji as icons |
| Always pair `focus:outline-none` with `focus:ring-*` | Remove focus outline without replacement |
