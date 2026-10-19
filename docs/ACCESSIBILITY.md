# Accessibility

Half the compliance team is over 50, and some agents will use screen magnifiers or screen
readers. The app aims at WCAG 2.2 AA, and at AAA for text contrast.

## How it's built

- **Large text and targets:** 20-pixel base size (18 on narrow screens), and the main
  buttons at least 52 pixels tall.
- **High contrast:** every text color meets WCAG AAA (7:1) against its background.
- **Never color alone:** every result has a word and an icon as well as a color (Matches,
  Check this, Problem, Not needed). Missing and extra warning words are announced as
  "missing:" and "added:" to screen readers, not only struck through or underlined.
- **Plain HTML controls:** real buttons, links, file inputs, and `<details>` for the folded
  sections, so everything works by keyboard. Drag and drop is an extra; the file buttons do
  the same job.
- **A visible focus ring:** a thick yellow outline with a dark edge, visible on light and
  dark backgrounds.
- **Announcements:** errors are a summary that takes focus. Chosen files, "Checking the
  label", and batch progress are announced politely. After a check, focus moves to the
  results heading.
- **Windows High Contrast mode:** badges and summaries keep their borders.

## Checked so far (Oct 19, 2026)

| Check | How | Result |
|---|---|---|
| Labels on every form control, alt text on every picture, page language, one `h1`, results not by color alone | Automated tests on every kind of page (`tests/web/test_accessibility.py`) | Pass |
| Text contrast, focus ring, control borders, every button and drop-zone state | Automated tests on the style sheet (`tests/web/test_style_sheet.py`) | Pass, after one fix: the busy Check button's gray was darkened from 4.8:1 to 7.6:1 |
| 200% zoom (a 1280-pixel window seen at 640 pixels) | Screenshots of the home page, a result, and a batch in headless Chrome | Pass: tables turn into stacked cards, nothing is cut off |
| 400% zoom (320 pixels wide, WCAG 1.4.10) | The same pages at 320 pixels | Pass, after one fix: the picture box on the home page didn't shrink to fit, and cut off its hint text. Now tested. |
| Every interaction reachable by keyboard | Read through the templates and script: no custom clickable elements, no positive `tabindex` | Pass |

## Still to do by a person

- **A keyboard-only run-through** of a single check and a batch, start to finish, in a real
  browser.
- **A screen reader spot check** with VoiceOver (macOS) or NVDA (Windows): the home page, a
  result with a Problem, and a batch in progress.
