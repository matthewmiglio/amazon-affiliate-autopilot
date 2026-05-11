"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="mx-auto max-w-xl px-6 py-24 text-center">
      <p className="text-xs uppercase tracking-[0.28em] text-gold">Error</p>
      <h1 className="font-serif-display mt-2 text-4xl text-ink md:text-5xl">
        Something went wrong.
      </h1>
      <p className="mt-5 text-base leading-relaxed text-muted">
        We hit an unexpected error rendering this page. Please try again.
      </p>
      <button
        onClick={reset}
        className="mt-8 inline-flex items-center rounded-full border border-ink px-6 py-3 text-sm text-ink transition hover:bg-ink hover:text-[color:var(--background)]"
      >
        Try again
      </button>
    </div>
  );
}
