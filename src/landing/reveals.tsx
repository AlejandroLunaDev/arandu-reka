"use client";

import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useEffect } from "react";

// Page motion. The first scene's copy comes in on load; every other scene's copy, and its art
// ([data-reveal-art]), come in with the scroll. The 3D rooms follow their anchors, so they move with
// the art. Nothing moves for people who ask for reduced motion.
export function Reveals() {
  useEffect(() => {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    gsap.registerPlugin(ScrollTrigger);
    const ctx = gsap.context(() => {
      const [first, ...rest] = gsap.utils.toArray<HTMLElement>("[data-scene]");
      if (first) {
        gsap.from(first.querySelectorAll("[data-reveal]"), {
          y: 16,
          opacity: 0,
          duration: 0.8,
          stagger: 0.08,
          ease: "power2.out",
          delay: 0.15,
        });
      }
      for (const scene of rest) {
        const tl = gsap.timeline({
          scrollTrigger: { trigger: scene, start: "top 75%", end: "top 10%", scrub: 0.6 },
        });
        tl.fromTo(
          scene.querySelectorAll("[data-reveal]"),
          { y: 24, opacity: 0 },
          { y: 0, opacity: 1, stagger: 0.08, ease: "none" },
          0,
        );
        const art = scene.querySelectorAll("[data-reveal-art]");
        if (art.length) tl.fromTo(art, { y: 60 }, { y: 0, ease: "none" }, 0);
      }
    });
    return () => ctx.revert();
  }, []);

  return null;
}
