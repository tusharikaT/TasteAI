---
name: TasteAI
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#3a3939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1c1b1b'
  surface-container: '#201f1f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353534'
  on-surface: '#e5e2e1'
  on-surface-variant: '#e4beb4'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#ab8980'
  outline-variant: '#5b4039'
  surface-tint: '#ffb5a0'
  primary: '#ffb5a0'
  on-primary: '#5f1500'
  primary-container: '#ff5722'
  on-primary-container: '#541200'
  inverse-primary: '#b02f00'
  secondary: '#ffd799'
  on-secondary: '#432c00'
  secondary-container: '#feb300'
  on-secondary-container: '#6a4800'
  tertiary: '#78dc77'
  on-tertiary: '#00390a'
  tertiary-container: '#41a447'
  on-tertiary-container: '#003208'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdbd1'
  primary-fixed-dim: '#ffb5a0'
  on-primary-fixed: '#3b0900'
  on-primary-fixed-variant: '#862200'
  secondary-fixed: '#ffdeac'
  secondary-fixed-dim: '#ffba38'
  on-secondary-fixed: '#281900'
  on-secondary-fixed-variant: '#604100'
  tertiary-fixed: '#94f990'
  tertiary-fixed-dim: '#78dc77'
  on-tertiary-fixed: '#002204'
  on-tertiary-fixed-variant: '#005313'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353534'
typography:
  display-hero:
    fontFamily: Playfair Display
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-hero-mobile:
    fontFamily: Playfair Display
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 42px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Playfair Display
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  container-max: 1280px
  gutter: 24px
  margin-mobile: 20px
  margin-desktop: 48px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style
The design system for this product is centered on a **Premium, High-End Culinary** experience. It targets discerning food enthusiasts who value precision and atmosphere. The aesthetic is a fusion of **Modern Minimalism** and **Glassmorphism**, creating a digital environment that feels like a dimly lit, upscale lounge. 

The emotional response should be one of "exclusive discovery." By utilizing deep blacks and warm, glowing accents, the UI recedes to let high-resolution food photography become the protagonist. Subtle translucency and blurred layers provide a sense of physical depth and sophistication.

## Colors
The palette is rooted in a "Noir-Gourmet" theme. The primary background is nearly pitch black to maximize contrast with the vibrant colors of food. 

- **Primary (Deep Orange):** Used for critical actions, brand presence, and highlighting the "AI engine" elements.
- **Secondary (Golden Amber):** Reserved exclusively for ratings, prestige indicators, and "premium" tier statuses.
- **Surface Strategy:** Surfaces use subtle shifts from `#1A1A1A` to `#1E1E1E` to define hierarchy without the need for heavy borders.
- **Hero Area:** Employs a warm, dark amber gradient to evoke the feeling of a candlelit table.

## Typography
This design system uses a sophisticated pairing of **Playfair Display** and **Inter**. 

- **Playfair Display** is reserved for high-level "Editorial" moments: restaurant names, hero headings, and section titles. It provides the high-end, "menu-like" feel.
- **Inter** handles all functional UI, data-heavy content, and AI-generated descriptions. Its neutral, systematic nature ensures clarity even at small sizes.
- **Hierarchy Tip:** Use `label-sm` in uppercase with wider tracking for meta-data like "CUISINE TYPE" or "DISTANCE" to maintain a clean, organized look.

## Layout & Spacing
The system utilizes a **Fluid Grid** that scales from mobile-first simplicity to a structured multi-column desktop experience.

- **Mobile (390px):** Single column with 20px side margins. Cards span the full width of the safe area.
- **Tablet (768px):** 2-column masonry or grid for restaurant listings. 
- **Desktop (1280px):** 12-column grid. Restaurant listings transition to a 3-column layout. 
- **Vertical Rhythm:** Use the `stack` variables to maintain consistent padding between sections (32px) and elements within a card (16px).

## Elevation & Depth
Depth is created through **Glassmorphism** and **Warm Glows**.

- **Surfaces:** Floating elements (like the NavBar or Hovered Cards) use a backdrop filter (`blur(12px)`) and a semi-transparent background (`rgba(26, 26, 26, 0.8)`).
- **Shadows:** Instead of neutral grey shadows, use "Deep Warm Glows." These are low-opacity, high-spread shadows with a slight tint of the primary color: `0px 10px 30px rgba(255, 87, 34, 0.15)`.
- **Z-Axis:** The sticky NavBar always sits at the highest elevation, using a thin `1px` border of `rgba(255, 255, 255, 0.1)` to define its edge against the scrollable content.

## Shapes
The shape language is a mix of geometric precision and organic softness.

- **Restaurant Cards:** Use the `rounded-lg` (16px) radius to feel substantial yet approachable.
- **Input Fields:** Use the `rounded-md` (12px) radius for a modern, tactile feel.
- **Interactive Pills:** Always use `rounded-full` (999px) for PreferenceChips and BudgetToggles to distinguish them from structural card elements.

## Components
- **Sticky NavBar:** Frosted glass effect (`blur(20px)`) with a subtle bottom border. Icons should be thin-stroke (2pt) to maintain the premium feel.
- **RestaurantCard:** Contains a large image header. Below the image, an "AI Explanation Block" uses a subtle primary-tinted background to explain why the user will like the venue.
- **PreferenceChips:** Selectable pills. Default state: `surface-secondary` with a thin border. Selected state: `primary-color` background with white text.
- **BudgetToggle:** A 3-segment horizontal control (`$`, `$$`, `$$$`). Use a sliding pill animation to indicate the active selection.
- **RatingStars:** Custom-shaped stars using the `secondary-color` (Golden Amber).
- **AISummaryBanner:** Featured at the top of search results. It features a gradient border (Primary to Secondary) and uses the `hero-gradient` as its internal background.
- **LoadingSpinner:** A circular ring that pulses in and out using a gradient stroke of the primary color, suggesting the "AI is thinking."
- **EmptyState:** High-contrast line-art illustrations centered with a muted `body-md` description.