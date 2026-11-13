"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import { GITHUB_URL } from "../links";
import styles from "./site-nav.module.css";

// The bar stays flat over the hero and draws its bottom border once the page moves.
export function SiteNav() {
  const [raised, setRaised] = useState(false);

  useEffect(() => {
    const onScroll = () => setRaised(scrollY > 8);
    onScroll();
    addEventListener("scroll", onScroll, { passive: true });
    return () => removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav className={styles.nav} data-raised={raised} aria-label="Arandu Reka">
      <Image src="/img/head.svg" alt="" width={24} height={24} priority />
      <span className="type-h3">Arandu Reka</span>
      <a className={`ar-btn ar-btn--ghost ar-btn--sm ${styles.end}`} href={GITHUB_URL}>
        Ver no GitHub
      </a>
    </nav>
  );
}
