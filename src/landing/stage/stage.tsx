"use client";

import { useEffect, useRef } from "react";
import styles from "./stage.module.css";

// The 3D layer over the landing. three.js loads in its own chunk, after the page is up, so the
// first paint never waits for it.
export function Stage() {
  const host = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    let stop: (() => void) | null = null;
    let cancelled = false;
    import("./run-stage")
      .then(({ runStage }) => {
        if (!cancelled) stop = runStage(el);
      })
      .catch((error: unknown) => {
        console.error("The 3D stage could not load", error);
        document.documentElement.classList.add("no3d");
      });
    return () => {
      cancelled = true;
      stop?.();
    };
  }, []);

  return <div ref={host} className={styles.stage} aria-hidden="true" />;
}
