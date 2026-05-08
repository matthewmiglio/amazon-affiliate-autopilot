import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Page not found",
  robots: { index: false, follow: false },
};

export default function NotFound() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col items-start px-6 pb-24 pt-24">
      <p className="text-xs uppercase tracking-[0.28em] text-gold">404</p>
      <h1 className="font-serif-display mt-2 text-4xl text-ink md:text-5xl">
        We can&rsquo;t find that page
      </h1>
      <p className="mt-5 max-w-xl leading-relaxed text-muted">
        The link may be outdated, or the page may have moved. Head back to the
        edit and keep browsing.
      </p>
      <div className="mt-8 flex gap-4 text-sm">
        <Link
          href="/"
          className="rounded-full border border-line px-5 py-2 text-ink transition hover:bg-ink hover:text-[color:var(--background)]"
        >
          Home
        </Link>
        <Link
          href="/products"
          className="rounded-full border border-line px-5 py-2 text-ink transition hover:bg-ink hover:text-[color:var(--background)]"
        >
          Shop the edit
        </Link>
      </div>
    </div>
  );
}
