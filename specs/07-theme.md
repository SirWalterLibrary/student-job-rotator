# 07 — Islamic theme

Goal: calm, dignified, geometric — emerald, gold and cream. Use only abstract geometry, arabesque patterns and calligraphic
text. Never draw people or animals. All assets are inline CSS/SVG (no downloads, no CDN).

## Design tokens (css/theme.css)
```css
:root {
  --emerald-900: #0b3d2e;   /* header, headings */
  --emerald-700: #14664a;   /* primary buttons, active tab */
  --emerald-500: #1f8a63;   /* hover, accents */
  --emerald-100: #dff0e8;   /* table stripes, chips */
  --gold-500:   #c9a227;    /* ornament, borders, today ring */
  --gold-300:   #e6cf7a;    /* ornament on dark */
  --cream:      #fbf6e9;    /* page background */
  --sand:       #f1e8cf;    /* cards */
  --ink:        #1d2b26;    /* body text */
  --ink-soft:   #51635b;    /* secondary text */
  --midnight:   #14213d;    /* dialogs header, cancelled day accent */
  --danger:     #a63d2f;
  --radius: 14px;
  --shadow: 0 2px 10px rgba(11, 61, 46, .12);
  --font-body: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --font-display: "Amiri", "Noto Naskh Arabic", "Scheherazade New", Georgia, serif;
}
```
Contrast rules: body text `--ink` on `--cream`/`--sand`. White text only on `--emerald-700` or darker.
`--gold-500` is for borders, rings and ornaments, and for text only on `--emerald-900` (use `--gold-300` there).
No gold text on cream. Verify AA for every text/background pair you introduce.

Fonts: do NOT load web fonts. `@font-face` is not needed; the stacks above fall back to installed fonts.
Arabic text uses `font-family: var(--font-display)`, larger line-height (1.8) and `lang="ar" dir="rtl"`.

## Background pattern (8-pointed star, "khatam")
Use as `background-image` on `body` (on `--cream`) and on the header plate (on `--emerald-900`, with `--gold-300` strokes).
```css
body {
  background-color: var(--cream);
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='60' height='60' viewBox='0 0 60 60'%3E%3Cg fill='none' stroke='%23c9a227' stroke-opacity='.28' stroke-width='1'%3E%3Crect x='15' y='15' width='30' height='30'/%3E%3Crect x='15' y='15' width='30' height='30' transform='rotate(45 30 30)'/%3E%3Ccircle cx='30' cy='30' r='4'/%3E%3C/g%3E%3C/svg%3E");
}
```
For the header, copy the same SVG with `stroke='%23e6cf7a'` and `stroke-opacity='.35'`.

## Components
- **Header plate**: `--emerald-900` background + star pattern, bottom border 4px `--gold-500`. Centered content with an arch
  top: `border-radius: 120px 120px 0 0 / 70px 70px 0 0` on an inner plate (max-width 720px) tinted `--emerald-700`.
  Inside: Bismillah, title, subtitle.
- **Bismillah** (exact text, copy it):
  `<p class="bismillah" lang="ar" dir="rtl">بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ</p>` — display font, ~1.8rem, `--gold-300`.
- **Title**: "Khidmah Roster" in display font; small Arabic `خدمة` next to it with `lang="ar"`.
- **Tabs**: pill/arch-shaped tabs. Active tab: `--emerald-700` background, white text, 3px `--gold-500` bottom border.
  Inactive: transparent, `--emerald-900` text, hover `--emerald-100`.
- **Day card**: `--sand` background, 1px `--gold-500` border, radius `--radius`, shadow; card header strip in `--emerald-900`
  with white/gold-300 text and a small 8-point star glyph `✶` before the date.
- **Table**: no vertical lines; row stripes `--emerald-100`; student names in display font, 1.25rem.
- **Badges**: "Today" = `--gold-500` background + `--emerald-900` text; "Upcoming" = `--emerald-100` + `--emerald-900`;
  "No class" = `--midnight` + white. Swap chip = outlined `--emerald-700` with ⇄.
- **Buttons**: primary = `--emerald-700` + white; secondary = outlined; destructive = `--danger` outline.
  Min height 44px, radius 999px.
- **Dialogs/drawer**: header strip `--midnight`, gold bottom rule, cream body.
- **Calendar cells**: `--sand`; Mon–Fri cells transparent with faint number; today ring 2px `--gold-500`;
  cancelled cells: `repeating-linear-gradient(45deg, transparent 0 6px, rgba(20,33,61,.08) 6px 12px)`.
- **Footer**: small `--ink-soft` text. Include `<span lang="ar" dir="rtl">جَزَاكُمُ ٱللَّهُ خَيْرًا</span>`
  followed by "Jazakum Allahu khayran".
- Motion: subtle 150ms transitions only; honor `prefers-reduced-motion`.

## Tone of microcopy
Warm and brief. Examples: empty roster → "No jobs yet — bismillah, add the first one." Saved → "Saved ✓".
Errors → plain sentences without blame.
