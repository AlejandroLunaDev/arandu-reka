import { Hero } from "./hero/hero";
import { KnowYouScene } from "./how-it-works/know-you-scene";
import { Reveals } from "./reveals";
import { SiteNav } from "./site-nav/site-nav";
import { Stage } from "./stage/stage";

// The landing page: scroll scenes under a fixed nav, and the 3D layer with Arandu over them.
export function LandingPage() {
  return (
    <>
      <SiteNav />
      <main className="overflow-x-clip">
        <Hero />
        <h2 className="sr-only">Como funciona</h2>
        <KnowYouScene />
      </main>
      <Stage />
      <Reveals />
    </>
  );
}
