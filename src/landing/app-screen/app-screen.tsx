"use client";

import { useEffect, useRef } from "react";
import styles from "./app-screen.module.css";

/** The width of the app's screens, in CSS pixels: the frame scales them down to fit. */
const SCREEN_WIDTH = 390;

type AppScreenProps = {
  /** A static screen of the app, under public/screens. */
  src: string;
  title: string;
};

// A phone showing one real screen of the app.
export function AppScreen({ src, title }: AppScreenProps) {
  const screen = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = screen.current;
    if (!el) return;
    const fit = () => el.style.setProperty("--k", String(el.clientWidth / SCREEN_WIDTH));
    const watcher = new ResizeObserver(fit);
    watcher.observe(el);
    fit();
    return () => watcher.disconnect();
  }, []);

  return (
    <div className={styles.phone}>
      <div ref={screen} className={styles.screen}>
        <iframe src={src} title={title} tabIndex={-1} loading="lazy" />
      </div>
    </div>
  );
}
