"use client";

import { useCallback, useEffect, useState } from "react";

type Section = { id: string; label: string };

export function TabNav({ sections }: { sections: Section[] }) {
  const [activeTab, setActiveTab] = useState(sections[0]?.id ?? "");

  const scrollToSection = useCallback((id: string) => {
    const el = document.getElementById(id);
    if (!el) return;
    const top = el.getBoundingClientRect().top + window.scrollY - 140;
    window.scrollTo({ top, behavior: "smooth" });
  }, []);

  useEffect(() => {
    const ratios = new Map<string, number>();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          ratios.set(entry.target.id, entry.intersectionRatio);
        }
        let best = "";
        let bestRatio = 0;
        for (const [id, ratio] of ratios) {
          if (ratio > bestRatio) {
            best = id;
            bestRatio = ratio;
          }
        }
        if (best && bestRatio > 0) setActiveTab(best);
      },
      { threshold: [0, 0.1, 0.25, 0.5, 0.75, 1] }
    );

    for (const s of sections) {
      const el = document.getElementById(s.id);
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, [sections]);

  return (
    <div className="sticky top-20 z-40 bg-[var(--bg)]/95 backdrop-blur border-b border-[var(--border)]">
      <div className="max-w-7xl mx-auto px-6">
        <nav className="flex gap-2 overflow-x-auto py-3">
          {sections.map((s) => {
            const active = activeTab === s.id;
            return (
              <button
                key={s.id}
                onClick={() => scrollToSection(s.id)}
                className={
                  "px-4 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors border " +
                  (active
                    ? "bg-[var(--accent)] text-[var(--bg)] border-[var(--accent)]"
                    : "bg-[var(--card)] text-[var(--muted)] border-[var(--border)] hover:text-[var(--fg)]")
                }
              >
                {s.label}
              </button>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
