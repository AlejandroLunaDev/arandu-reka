import Image from "next/image";
import { AppScreen } from "../app-screen/app-screen";
import { GITHUB_URL } from "../links";
import { Scene } from "../scene/scene";
import styles from "./hero.module.css";

// The hero: the title, and under it the app's path on a phone beside the pitch. On the right, the
// room where Arandu waits: the stage draws it in 3D, the page only keeps its place in the layout.
export function Hero() {
  return (
    <Scene
      length="hero"
      labelledBy="hero-title"
      copy={
        <div className={styles.intro}>
          <div className={styles.head}>
            <p data-reveal className="type-caption uppercase text-text-muted">
              Arandu Reka
            </p>
            <h1 id="hero-title" data-reveal className="type-display text-balance">
              A busca da sabedoria começa por você.
            </h1>
          </div>
          <div data-reveal className={styles.app}>
            <AppScreen src="/screens/B1-Mapa.html" title="Tela do app: o caminho de uma carreira, estante por estante" />
          </div>
          <div className={styles.pitch}>
            <p data-reveal className="type-body-lg text-pretty text-text-muted">
              Um app de orientação vocacional com inteligência artificial, onde o aluno do ensino médio vive
              uma carreira antes de escolher.
            </p>
            <div data-reveal className="flex flex-wrap items-center gap-2">
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
          </div>
        </div>
      }
      art={
        <span data-room="hero" className={styles.room}>
          <Image className={styles.fallback} src="/img/cat.svg" alt="" width={600} height={370} />
        </span>
      }
    />
  );
}
