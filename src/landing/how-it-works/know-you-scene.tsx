import Image from "next/image";
import { AppScreen } from "../app-screen/app-screen";
import { Scene } from "../scene/scene";
import styles from "./know-you-scene.module.css";

// How it works, step 1: the first questions, on the phone. Beside it, the stage draws two shelves
// where the cat waits.
export function KnowYouScene() {
  return (
    <Scene
      id="como"
      length="step"
      flip
      labelledBy="know-you-title"
      copy={
        <>
          <p data-reveal className="type-caption uppercase text-text-muted">
            Como funciona · <span className="text-accent-text">1</span> de 4
          </p>
          <h3 id="know-you-title" data-reveal className="type-h1 text-balance">
            O Arandu te conhece.
          </h3>
          <p data-reveal className="type-body-lg text-pretty text-text-muted">
            Perguntas rápidas, uma de cada vez, sobre o que você curte, o que faz bem e o que te desafia.
          </p>
        </>
      }
      art={
        <div data-reveal-art className={styles.art}>
          <AppScreen src="/screens/A4-Pergunta-tempo-livre.html" title="Tela do app: uma pergunta do questionário" />
          <span data-room="know-you" className={styles.room}>
            <Image className={styles.fallback} src="/img/cat.svg" alt="" width={600} height={370} />
          </span>
        </div>
      }
    />
  );
}
