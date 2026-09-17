# Starter UI review

Reviewed 17 September 2026 against the completed project's frontend. Read-only implementation review plus an isolated Playwright browser session (`starter-ui-review`) at 1280×720 and 390×844. Test writes used customer `review-ui-20260917`.

## Findings

1. **Medium: mobile rewards clip the primary action.** At 390px, the reward table's 360px minimum width exceeds the card's available inner width. The Action heading is offscreen and Claim buttons are cut off. Evidence: `output/playwright/starter-ui-review-mobile-rewards.png`. Remove the fixed minimum width for this table and allocate compact price/action columns, or render reward cards on narrow screens. Verify all claim buttons at 320px and 390px without horizontal scrolling. Reported to the parent for correction.
2. **Low: duplicate accessible Move money heading.** The visible page heading is followed by a second screen-reader-only heading with the same text. This creates redundant heading navigation. Remove the hidden duplicate, retaining the visible heading and form section titles. Source: `app/frontend/src/App.jsx`, money view. Reported to the parent for correction.
3. **Low: missing favicon request.** Initial browser load emitted a 404 for `/favicon.ico`. Add a local favicon and link it in `index.html`. Parent confirmed this finding independently and began fixing it during review.

## Verified strengths

- The starter uses the completed app's green palette, raised buttons, neutral background, compact centered shell, white cards, tab underline, typography, spacing, and restrained motion.
- Desktop overview is readable and visually consistent. Evidence: `output/playwright/starter-ui-review-desktop.png`.
- At 390px the money forms stack cleanly; customer field, navigation, labels, input controls, and submit buttons remain usable. Evidence: `output/playwright/starter-ui-review-mobile-money.png`.
- Navigation and form controls expose accessible names; main navigation has a label, current page is declared, and status/error feedback has appropriate live roles. Tables have focusable scroll containers.
- A €1,000 deposit for the isolated review customer produced visible +1,000-point feedback and reachable catalogue claim controls. Claim opens a named confirmation dialog with warning text.
- No UI for login, account creation, weekly streaks, loyalty bonuses, gifting, or notifications appeared. Deposit anniversaries remain in the pre-bonus deposit-lot display; this alone does not implement a loyalty reward.
- Source inspection confirms visible focus styling, reduced-motion handling, native modal dialog use, Escape handling, and intended focus restoration.

## Limits and follow-up

The parent began applying feedback while this review was open; hot reload reset the page during the dedicated keyboard focus-cycle check. Therefore this report does not claim a completed live focus-trap test. The parent's durable browser smoke test should verify initial Cancel focus, Tab containment, Escape dismissal, and return to the originating Claim button after the final implementation. No automated contrast audit was run.

Findings describe the reviewed state before the feedback pass. Recheck the final mobile rewards screenshot after the fixes.

## Feedback verification

After a fresh reload, the corrected rewards table fits both 390px and 320px viewports: its scroll width equals its available width (332px and 262px respectively), and the page has no horizontal overflow. Evidence: `output/playwright/starter-ui-review-rewards-fixed-390.png` and `output/playwright/starter-ui-review-rewards-fixed-320.png`. The duplicate heading was removed and favicon link added in source.

The live claim keyboard check confirmed initial focus on Cancel, Tab to Confirm claim, Escape dismissal, and restored focus on the originating Claim button. A second Tab temporarily focused the browser/body rather than another application control; final smoke should allow browser chrome traversal inherent to native dialogs. No remaining blocking UI findings.
