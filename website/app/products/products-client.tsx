"use client";

import { useMemo, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import type { Product } from "@/lib/products";

type Props = {
  products: Product[];
  categories: string[];
};

export default function ProductsClient({ products, categories }: Props) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<string>("all");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return products.filter((p) => {
      if (category !== "all" && p.category !== category) return false;
      if (!q) return true;
      const hay = `${p.brand} ${p.product}`.toLowerCase();
      return hay.includes(q);
    });
  }, [products, query, category]);

  return (
    <div className="mx-auto max-w-6xl px-6 pb-24 pt-16">
      <header className="mb-10 max-w-2xl">
        <p className="text-xs uppercase tracking-[0.28em] text-gold">
          The full edit
        </p>
        <h1 className="font-serif-display mt-2 text-4xl text-ink md:text-5xl">
          Shop the edit
        </h1>
        <p
          className="text-base leading-relaxed text-muted"
          style={{ marginTop: "1.5rem" }}
        >
          {products.length} carefully chosen pieces. Filter by category or
          search by brand or product. Tap any piece to read more.
        </p>
      </header>

      {/* Filters */}
      <div style={{ marginBottom: "2.5rem" }}>
        <div className="relative" style={{ marginBottom: "1.5rem" }}>
          <input
            type="search"
            placeholder="Search by brand or product"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full rounded-full border border-line bg-[color:var(--background)] py-3 px-7 text-sm text-ink placeholder:text-muted/80 shadow-[0_1px_0_rgba(0,0,0,0.02)] transition focus:border-ink focus:outline-none"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setCategory("all")}
            className={chipClass(category === "all")}
          >
            <span>All</span>
            <span style={{ opacity: 0.7 }}>{products.length}</span>
          </button>
          {categories.map((c) => {
            const count = products.filter((p) => p.category === c).length;
            const active = category === c;
            return (
              <button
                key={c}
                type="button"
                onClick={() => setCategory(c)}
                className={chipClass(active)}
              >
                <span>{c}</span>
                <span style={{ opacity: 0.7 }}>{count}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div
        className="flex items-center justify-between border-t border-line/70"
        style={{ marginBottom: "2rem", paddingTop: "1.5rem" }}
      >
        <p className="text-xs uppercase tracking-[0.18em] text-muted">
          {filtered.length} {filtered.length === 1 ? "result" : "results"}
        </p>
        {(query || category !== "all") && (
          <button
            type="button"
            onClick={() => {
              setQuery("");
              setCategory("all");
            }}
            className="text-xs uppercase tracking-[0.18em] text-muted underline-offset-4 hover:text-ink hover:underline"
          >
            Clear filters
          </button>
        )}
      </div>

      {filtered.length === 0 ? (
        <p className="text-muted">
          No matches. Try a different search or category.
        </p>
      ) : (
        <ul className="grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          {filtered.map((p) => (
            <li
              key={p.slug}
              className="group overflow-hidden rounded-2xl border border-line bg-[color:var(--background)] transition hover:shadow-md"
            >
              <Link
                href={`/p/${p.slug}`}
                className="block"
              >
                <div className="relative aspect-square overflow-hidden bg-white">
                  <Image
                    src={p.image}
                    alt={`${p.brand} ${p.product}`}
                    fill
                    sizes="(max-width: 640px) 100vw, (max-width: 768px) 50vw, (max-width: 1024px) 33vw, 25vw"
                    className="object-contain p-5 transition duration-500 group-hover:scale-[1.03]"
                  />
                </div>
                <div className="flex flex-col gap-1 p-5">
                  <p className="text-[10px] uppercase tracking-[0.18em] text-gold">
                    {p.brand}
                  </p>
                  <p className="line-clamp-2 text-sm text-ink">{p.product}</p>
                  <div className="mt-2 flex items-center justify-end">
                    <span className="text-xs text-muted underline-offset-4 group-hover:text-ink group-hover:underline">
                      View details →
                    </span>
                  </div>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function chipClass(active: boolean) {
  return [
    "inline-flex items-center gap-2 rounded-full border px-5 py-2 text-xs uppercase tracking-[0.14em] leading-none transition cursor-pointer text-ink",
    active
      ? "border-ink bg-background"
      : "border-line bg-rose-soft hover:border-ink",
  ].join(" ");
}
