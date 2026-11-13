import Image from "next/image";
import { GITHUB_URL } from "../links";
import { Scene } from "../scene/scene";
import styles from "./hero.module.css";

// The hero: the title on the left, the room on the right. The room itself is 3D, drawn by the stage
// over this anchor; the anchor only keeps its place in the layout.
export function Hero() {
  return (
    <Scene
      length="hero"
      labelledBy="hero-title"
      copy={
        <>
          <p data-reveal className="type-caption uppercase text-text-muted">
            Arandu Reka
          </p>
          <h1 id="hero-title" data-reveal className="type-display text-balance">
            A busca da sabedoria começa por você.
          </h1>
          <p data-reveal className="type-body-lg text-pretty text-text-muted">
            Um app de orientação vocacional com inteligência artificial, onde o aluno do ensino médio vive
            uma carreira antes de escolher.
          </p>
          <div data-reveal className="flex flex-wrap items-center gap-2 pt-2">
            <a className="ar-btn ar-btn--primary" href="#como">
              <svg className="ar-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 5v14" />
                <path d="m6 13 6 6 6-6" />
              </svg>
              Como funciona
            </a>
            <a className="ar-btn ar-btn--ghost" href={GITHUB_URL}>
              Ver no GitHub
            </a>
          </div>
        </>
      }
      art={
        <span data-room="hero" className={styles.room}>
          <Image className={styles.fallback} src="/img/cat.svg" alt="" width={600} height={370} />
        </span>
      }
    />
  );
}
