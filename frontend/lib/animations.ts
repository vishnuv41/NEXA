import anime from "animejs";

/**
 * Animate page entrance: smoothly fade in and translateY cards and sections
 */
export function animatePageTransition(target = ".anime-fade-in") {
  if (typeof window === "undefined") return;
  try {
    anime.remove(target);
    anime({
      targets: target,
      opacity: [0, 1],
      translateY: [10, 0],
      delay: anime.stagger(40, { start: 10 }),
      duration: 380,
      easing: "easeOutCubic",
    });
  } catch {
    // Fallback gracefully
  }
}

/**
 * Animate mode switch: gently pop the mode indicator badge and buttons
 */
export function animateModeSwitch(target = ".anime-mode-indicator") {
  if (typeof window === "undefined") return;
  try {
    anime.remove(target);
    anime({
      targets: target,
      scale: [0.92, 1.05, 1],
      duration: 380,
      easing: "easeOutElastic(1, 0.7)",
    });
  } catch {
    // Fallback gracefully
  }
}

/**
 * Animate pulse on live update or incoming event
 */
export function animateLivePulse(target = ".anime-live-pulse") {
  if (typeof window === "undefined") return;
  try {
    anime.remove(target);
    anime({
      targets: target,
      scale: [1, 1.03, 1],
      duration: 280,
      easing: "easeOutQuad",
    });
  } catch {
    // Fallback gracefully
  }
}
