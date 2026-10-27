// Keeps a dropdown panel inside the screen: it opens under its button, lined up
// with the button's left edge, and moves left as far as needed so it doesn't run
// off the right side (which would make the whole page scroll sideways).

const MARGIN = 8 // px kept free at the screen edge

export function keepOnScreen(panel: HTMLElement | undefined) {
  if (!panel) return
  panel.style.left = '0px'
  const overflow = panel.getBoundingClientRect().right - (document.documentElement.clientWidth - MARGIN)
  if (overflow > 0) panel.style.left = `${-overflow}px`
}
