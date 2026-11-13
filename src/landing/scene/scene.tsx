import type { ReactNode } from "react";
import styles from "./scene.module.css";

type SceneProps = {
  /** How long the scene stays pinned while the page scrolls: the hero is shorter than a step. */
  length: "hero" | "step";
  /** Puts the art on the left of the copy on wide screens. */
  flip?: boolean;
  id?: string;
  labelledBy: string;
  copy: ReactNode;
  art: ReactNode;
};

// A scroll scene: a tall section whose content stays pinned to the viewport while the page moves,
// the copy on one side and the art on the other. The 3D stage finds it through [data-scene].
export function Scene({ length, flip = false, id, labelledBy, copy, art }: SceneProps) {
  return (
    <section
      id={id}
      data-scene
      aria-labelledby={labelledBy}
      className={`${styles.scene} ${styles[length]} ${flip ? styles.flip : ""}`}
    >
      <div data-pin className={styles.pin}>
        <div className={styles.copy}>{copy}</div>
        <div className={styles.art}>{art}</div>
      </div>
    </section>
  );
}
