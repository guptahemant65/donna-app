---
name: Donna — The Void
description: A conversational AI concierge rendered as a presence in darkness. No chrome, no dashboard. Just a voice in the void.
colors:
  primary: "#f43f5e"
  on-primary: "#050507"
  primary-container: "rgba(244,63,94,0.12)"
  on-primary-container: "#fda4af"
  surface: "#050507"
  surface-dim: "#030304"
  surface-bright: "#18181b"
  surface-container-lowest: "#030304"
  surface-container-low: "#0a0a0d"
  surface-container: "#0f0f12"
  surface-container-high: "#18181b"
  surface-container-highest: "#27272a"
  on-surface: "#d4d4d8"
  on-surface-variant: "#71717a"
  inverse-surface: "#fafafa"
  inverse-on-surface: "#050507"
  outline: "#3f3f46"
  outline-variant: "#27272a"
  surface-tint: "#f43f5e"
  secondary: "#a78bfa"
  on-secondary: "#1e1b4b"
  secondary-container: "rgba(167,139,250,0.1)"
  on-secondary-container: "#c4b5fd"
  tertiary: "#22d3ee"
  on-tertiary: "#083344"
  tertiary-container: "rgba(34,211,238,0.08)"
  on-tertiary-container: "#67e8f9"
  error: "#ef4444"
  on-error: "#450a0a"
  error-container: "rgba(239,68,68,0.12)"
  on-error-container: "#fca5a5"
  background: "#050507"
  on-background: "#d4d4d8"
  ghost: "#3f3f46"
  aurora-deep-navy: "#0a0a1a"
  aurora-dark-violet: "#0d0a18"
  aurora-dark-teal: "#070d12"
typography:
  display-lg:
    fontFamily: Space Grotesk
    fontSize: 48px
    fontWeight: "700"
    lineHeight: 56px
    letterSpacing: -0.03em
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 24px
    fontWeight: "600"
    lineHeight: 32px
    letterSpacing: -0.02em
  body-lg:
    fontFamily: Space Grotesk
    fontSize: 15px
    fontWeight: "400"
    lineHeight: 1.7em
    letterSpacing: 0em
  body-md:
    fontFamily: Space Grotesk
    fontSize: 13px
    fontWeight: "400"
    lineHeight: 1.6em
    letterSpacing: 0em
  label-sm:
    fontFamily: Space Grotesk
    fontSize: 11px
    fontWeight: "500"
    lineHeight: 16px
    letterSpacing: 0.1em
  label-xs:
    fontFamily: Space Grotesk
    fontSize: 10px
    fontWeight: "300"
    lineHeight: 14px
    letterSpacing: 0.15em
  mono-md:
    fontFamily: Space Mono
    fontSize: 13px
    fontWeight: "400"
    lineHeight: 1.5em
    letterSpacing: 0em
  sender-donna:
    fontFamily: Space Grotesk
    fontSize: 12px
    fontWeight: "600"
    lineHeight: 16px
    letterSpacing: 0.02em
  sender-user:
    fontFamily: Space Grotesk
    fontSize: 12px
    fontWeight: "400"
    lineHeight: 16px
    letterSpacing: 0.02em
rounded:
  none: 0px
  sm: 2px
  md: 4px
  lg: 8px
  xl: 12px
spacing:
  unit: 8px
  message-gap: 28px
  rich-content-padding: 16px
  input-padding-bottom: 20px
  conversation-padding-top: 80px
  conversation-padding-bottom: 40px
  content-max-width: 780px
  message-max-width: 65%
components:
  message-donna:
    textColor: "{colors.on-surface}"
    typography: "{typography.body-lg}"
  message-donna-name:
    textColor: "{colors.primary}"
    typography: "{typography.sender-donna}"
  message-user:
    textColor: "{colors.on-surface}"
    typography: "{typography.body-lg}"
  message-user-name:
    textColor: "{colors.on-surface-variant}"
    typography: "{typography.sender-user}"
  message-timestamp:
    textColor: "{colors.ghost}"
    typography: "{typography.label-xs}"
  rich-content-block:
    backgroundColor: transparent
    textColor: "{colors.on-surface}"
    rounded: "{rounded.none}"
    padding: "{spacing.rich-content-padding}"
  rich-content-incident:
    textColor: "{colors.on-surface}"
    typography: "{typography.body-md}"
  rich-content-label:
    textColor: "{colors.ghost}"
    typography: "{typography.label-sm}"
  rich-content-data:
    textColor: "{colors.on-surface}"
    typography: "{typography.mono-md}"
  input-field:
    backgroundColor: transparent
    textColor: "{colors.on-surface}"
    typography: "{typography.body-lg}"
  input-line:
    backgroundColor: "rgba(255,255,255,0.12)"
  input-line-active:
    backgroundColor: "{colors.primary}"
  input-hint:
    textColor: "{colors.ghost}"
    typography: "{typography.label-xs}"
  command-option:
    textColor: "{colors.on-surface-variant}"
    typography: "{typography.body-md}"
  command-option-hover:
    textColor: "{colors.on-surface}"
  toast-default:
    textColor: "{colors.on-surface-variant}"
    typography: "{typography.body-md}"
  toast-critical:
    textColor: "{colors.primary}"
    typography: "{typography.body-md}"
  sprint-bar-fill:
    backgroundColor: "rgba(244,63,94,0.25)"
  sprint-bar-track:
    backgroundColor: "rgba(255,255,255,0.04)"
  sprint-bar-label:
    textColor: "{colors.on-surface-variant}"
    typography: "{typography.mono-md}"
---

## Overview

Donna is a void. Not a dashboard, not a chat app, not a tool. A presence in darkness.

The design philosophy is **radical absence**: there is no UI chrome. No sidebar, no tabs, no header, no toolbar, no status bar, no window border. The entire interface is a conversation between two people — Harvey (the user) and Donna (the AI) — rendered on a near-black canvas that breathes with barely perceptible color.

The emotional register is **confident restraint**. Donna knows everything but says only what matters. The interface reflects this — information surfaces when needed and dissolves when done. The negative space between elements is as designed as the elements themselves.

**Groundbreaking elements:**
- A living aurora gradient at the canvas floor that breathes on a 30-second cycle using CSS `@property` animations
- Messages revealed via `clip-path` curtain-sweep animations
- A cursor-following spotlight effect using radial gradients
- A heartbeat-pulsing input line that serves as the app's visual anchor
- Seismograph-wave typing indicator instead of bouncing dots
- Scroll-fade masks that dissolve content at viewport edges

The interface should make someone ask "what IS this?" — not "which template is this?"

## Colors

Color is an EVENT, not a constant. The void is near-black. Text is cool gray. And then there is rose — used for exactly three things in the entire interface:

1. **Donna's name** — the only colored text element in the conversation
2. **The input caret and focus accent** — when the user engages, the void responds
3. **Critical status indicators** — Sev1 incidents, errors

Everything else is grayscale. This extreme restraint means that when rose appears, it carries meaning. It is Donna's signature — confident, precise, impossible to miss.

- **Primary (#f43f5e):** Rose. Donna's color. Bold, feminine-but-powerful, confident. NOT a background color. Only used for text and thin accent lines.
- **On-Surface (#d4d4d8):** Cool zinc gray for all body text. Not pure white — softer, easier on eyes in the void.
- **On-Surface-Variant (#71717a):** Secondary text — metadata, sender names (Harvey's), descriptions.
- **Ghost (#3f3f46):** Tertiary — timestamps (shown only on hover), hints, almost invisible.
- **Aurora colors:** Three deep tones (#0a0a1a navy, #0d0a18 violet, #070d12 teal) that cycle through a `@property`-animated gradient. Opacity capped at 0.4 — the user should barely consciously notice the aurora but feel the void is alive.

## Typography

One family. One voice. **Space Grotesk** — geometric, modern, distinctive but readable. It carries a technical precision without the sterility of system fonts and the preciousness of serif display fonts.

- **Hierarchy is weight, not size.** Most text is 13-15px. The difference between Donna's name and Harvey's is weight (600 vs 400) and color (rose vs gray), not font size.
- **Monospace (Space Mono)** is reserved for data: IcM IDs, PR numbers, branch names, cluster names, percentages. It creates a subtle "data layer" within the prose without needing borders or backgrounds.
- **No display sizes in the UI.** The app has no headings, no hero text, no titles. The largest text is the conversation at 15px. Everything communicates through density and contrast, not size.
- **Letter-spacing is a tool.** Labels use 0.1em tracking for quiet authority. Body text uses 0em for reading flow.

## Layout & Spacing

The layout is nothing. Literally nothing. The entire app is:

```
┌──────────────────────────────────────┐
│                                      │
│    [conversation messages scroll]    │
│                                      │
│    ─────────────────────────────     │
│    [input field]                     │
│    donna                    Ctrl+K   │
└──────────────────────────────────────┘
```

- The body IS the app. No window, no border, no card floating in space.
- Content is centered at `780px` max-width with `24px` horizontal padding.
- Messages stack vertically with `28px` gap — generous but not wasteful.
- Each message is left-aligned, max `65%` width — preventing wall-of-text fatigue.
- The conversation area uses scroll-fade masks: `mask-image` gradients that dissolve content to transparent at the top and bottom edges. This eliminates hard clip boundaries and makes scrolling feel like peering through a aperture.
- The input sits at the absolute bottom with a single 1px horizontal line as its only visual boundary.
- Below the input: "donna" on the left, "Ctrl+K" on the right, both in ghost text at opacity 0.2-0.35.

## Elevation & Depth

There are no cards, no shadows, no borders. Depth is achieved through three mechanisms:

1. **The Aurora** — A radial gradient fixed to the bottom 45% of the viewport, masked to fade upward. It creates a sense of standing at the edge of something vast. Colors cycle via `@property` custom properties on a 30-second alternate animation.

2. **The Spotlight** — A subtle radial gradient (350px diameter, rgba(255,255,255,0.018)) that follows the cursor position across the conversation area. It creates a flashlight-in-darkness effect that makes the text feel three-dimensional.

3. **The Cursor Trail** — A 250px rose-tinted blur (opacity 0.03) that follows the mouse with 150ms lag. Combined with the spotlight, it gives the void a sense of responsive presence.

These three layers create depth without any traditional elevation patterns. The void isn't flat — it's alive.

## Shapes

There are almost no shapes. This is intentional.

- **No rounded corners on messages** — text doesn't need containers.
- **Rich content blocks** use a 2px left border as their only shape. Rose for incidents, ghost gray for everything else. No background, no rounding.
- **The sprint progress bar** is 4px tall with 2px radius — barely a shape, more a data trace.
- **Command palette options** have no shape — just text that brightens on hover.
- **The input line** is 1px. That's it. The thinnest possible shape.

The absence of shapes IS the design language. Information is conveyed through typography and spacing, not containers.

## Components

### Messages

Messages are pure typography. No bubbles, no backgrounds, no borders. Sender name on one line (12px), message below (15px). Donna's messages use a **curtain reveal** animation: `clip-path: inset(0 100% 0 0)` transitioning to `inset(0 0% 0 0)` over 600ms. A thin reveal line sweeps left-to-right before the text appears. Harvey's messages simply fade in with translateY(10px → 0).

Timestamps are hidden by default. On hover, they appear to the right with `opacity: 0 → 0.4` over 200ms. This keeps the conversation clean until the user wants temporal context.

### Rich Content Blocks

When Donna references structured data (incidents, PRs, sprint), an inline block materializes. The materialization is the CSS showpiece: (1) hairline sweeps left→right 200ms, (2) content height expands via grid-template-rows 0fr→1fr 300ms, (3) content fades in 200ms after a 300ms delay. Total choreography: 700ms.

Rich blocks have a 2px left border (rose for incidents, ghost for others) and 16px left padding. No background. Type labels are 11px uppercase with 0.1em tracking. Data points use Space Mono. The block feels like an indented citation, not a card.

### Input & Heartbeat

The input is transparent with no border. The visual anchor is the 1px line below it, animated with a 4-second heartbeat (opacity 0.4 → 0.8 → 0.4). On focus, the heartbeat stops and a rose accent line bleeds outward from center (width 0% → 100% over 400ms with cubic-bezier(0.16, 1, 0.3, 1)). A conic-gradient glow rotates around the input area at 0.03 opacity.

### Command Palette

Ctrl+K triggers a transformation: backdrop-filter blur(12px) covers the conversation, and command options fade in below the input as horizontal text (no icons, no boxes). Hovering a command: brightness transitions from variant to full white with a subtle underline sweep. Escape reverses everything.

### Toast / Whisper

Notifications appear at bottom-right, max 0.5 opacity (0.7 for critical). They slide in with translateX(20px → 0) over 400ms, hold for 5 seconds, then exit with translateX(0 → -10px). They're whispers, not alerts — information at the periphery.

## Do's and Don'ts

### Do

- Use `@property` for all animated custom properties (aurora colors, glow angles, accent widths)
- Use `clip-path` for reveal animations — it's GPU-accelerated and crisp
- Use `mask-image` for scroll fades — eliminates hard content boundaries
- Use `backdrop-filter` for command palette overlay — creates physical depth
- Respect `prefers-reduced-motion` — disable all animations, show everything instantly
- Keep rose usage to exactly 3 contexts: Donna's name, input focus, critical status
- Let the void breathe — generous spacing, no dense grids, no crowded layouts

### Don't

- Don't add borders, cards, or containers around messages
- Don't use chat bubbles or message background colors
- Don't add a sidebar, tabs, toolbar, or traditional navigation
- Don't use serif fonts, display fonts, or Google Fonts beyond Space Grotesk/Mono
- Don't use warm colors (gold, amber, brown, espresso)
- Don't use gradients on text or as decorative backgrounds
- Don't use emoji — unicode symbols (▸, ●, ✓) only where functional
- Don't use bounce, spring, or elastic easing — use ease-out and cubic-bezier only
- Don't add a custom titlebar with minimize/maximize/close buttons
- Don't show timestamps by default — hover-reveal only
- Don't use ALL-CAPS for section headers in the conversation
