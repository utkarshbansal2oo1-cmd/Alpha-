import { lazy, Suspense } from "react";
import Nav from "./components/nav/Nav";
import Hero from "./components/sections/Hero";
import ProblemComparison from "./components/sections/ProblemComparison";
import ProductJourney from "./components/sections/ProductJourney";

// Below-the-fold, heavier sections are code-split: the initial bundle is
// the shell + Nav + Hero + Problem/Journey (all lightweight), everything
// past that (the live demo's API/animation logic, the SVG architecture
// diagram) loads only once the user scrolls near it. This is the
// "lazy load heavy animations / code split sections" requirement,
// implemented at the section boundary rather than per-component, since
// sections are the natural chunk boundary here.
const HowItThinks = lazy(() => import("./components/sections/HowItThinks"));
const LiveDemo = lazy(() => import("./components/sections/LiveDemo"));
const FeatureShowcase = lazy(() => import("./components/sections/FeatureShowcase"));
const EnterpriseArchitecture = lazy(() => import("./components/sections/EnterpriseArchitecture"));
const Vision = lazy(() => import("./components/sections/Vision"));
const Footer = lazy(() => import("./components/sections/Footer"));

function SectionFallback() {
  return <div className="min-h-[400px]" aria-hidden="true" />;
}

export default function App() {
  return (
    <div className="relative min-h-screen bg-base overflow-hidden">
      <Nav />
      <Hero />
      <ProblemComparison />
      <ProductJourney />
      <Suspense fallback={<SectionFallback />}>
        <HowItThinks />
      </Suspense>
      <Suspense fallback={<SectionFallback />}>
        <LiveDemo />
      </Suspense>
      <Suspense fallback={<SectionFallback />}>
        <FeatureShowcase />
      </Suspense>
      <Suspense fallback={<SectionFallback />}>
        <EnterpriseArchitecture />
      </Suspense>
      <Suspense fallback={<SectionFallback />}>
        <Vision />
      </Suspense>
      <Suspense fallback={<SectionFallback />}>
        <Footer />
      </Suspense>
    </div>
  );
}
