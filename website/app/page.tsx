import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { products } from "@/lib/products";

import { jsonLd, siteName, siteUrl } from "@/lib/seo";

const PILLARS = ["Beauty", "Fragrance", "Fashion", "Jewelry"];

export const metadata: Metadata = {
  alternates: { canonical: "/" },
};

export default function Home() {
  const featured = products.slice(0, 4);

  const itemListLd = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: `${siteName} — Featured finds`,
    itemListElement: featured.map((p, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: `${p.brand} ${p.product}`,
      url: `${siteUrl}/p/${p.slug}`,
      image: `${siteUrl}${p.image}`,
    })),
  };

  return (
    <div>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={jsonLd(itemListLd)}
      />
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-line">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-[0.18]"
        >
          <Image
            src="/brand/pink-gold-marble-abstract.png"
            alt=""
            fill
            sizes="100vw"
            className="object-cover"
            priority
          />
        </div>
        <div className="relative mx-auto grid max-w-6xl grid-cols-1 gap-10 px-6 py-20 md:grid-cols-12 md:py-28">
          <div className="md:col-span-7">
            <p className="mb-4 text-xs uppercase tracking-[0.28em] text-gold">
              Curated Daily · Amazon Associate
            </p>
            <h1 className="font-serif-display text-5xl leading-[1.05] text-ink md:text-7xl">
              The Luxe Drawer
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted">
              Daily Amazon luxury finds for women who want the look — without
              the markup. Beauty, fragrance, fashion and fine little objects,
              hand-picked and refreshed often.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link
                href="/products"
                className="inline-flex items-center justify-center rounded-full bg-ink px-7 py-3 text-sm font-medium tracking-wide text-[color:var(--background)] transition hover:bg-[#3a3330]"
              >
                Shop the edit
              </Link>
              <Link
                href="/about"
                className="inline-flex items-center justify-center rounded-full border border-line px-7 py-3 text-sm font-medium text-ink transition hover:border-ink"
              >
                Our story
              </Link>
            </div>
            <p className="mt-8 max-w-md text-xs leading-relaxed text-muted">
              As an Amazon Associate I earn from qualifying purchases. This
              means we may receive a small commission, at no cost to you, when
              you buy through links on this site.
            </p>
          </div>

          <div className="relative md:col-span-5">
            <div className="relative mx-auto aspect-[3/4] w-full max-w-sm overflow-hidden rounded-[2rem] border border-line shadow-sm">
              <Image
                src="/character/champagne-slip-head-tilted-dreamy.png"
                alt="The Luxe Drawer lifestyle"
                fill
                sizes="(max-width: 768px) 100vw, 40vw"
                className="object-cover"
                priority
              />
            </div>
          </div>
        </div>
      </section>

      {/* Pillars */}
      <section className="mx-auto max-w-6xl px-6 py-16">
        <div className="flex flex-wrap items-center justify-center gap-x-10 gap-y-4 text-center">
          {PILLARS.map((p, i) => (
            <span
              key={p}
              className="font-serif-display text-xl text-ink md:text-2xl"
            >
              {p}
              {i < PILLARS.length - 1 && (
                <span className="ml-10 text-gold">·</span>
              )}
            </span>
          ))}
        </div>
      </section>

      {/* Featured */}
      <section className="border-y border-line bg-rose-soft/30">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <div className="mb-10 flex items-end justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-gold">
                This week's edit
              </p>
              <h2 className="font-serif-display mt-2 text-3xl text-ink md:text-4xl">
                Featured finds
              </h2>
            </div>
            <Link
              href="/products"
              className="hidden text-sm text-muted underline-offset-4 hover:text-ink hover:underline md:block"
            >
              View all {products.length} →
            </Link>
          </div>

          <ul className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {featured.map((p) => (
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
                      sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 25vw"
                      className="object-contain p-5 transition duration-500 group-hover:scale-[1.03]"
                    />
                  </div>
                  <div className="p-5">
                    <p className="text-xs uppercase tracking-wider text-gold">
                      {p.brand}
                    </p>
                    <p className="mt-1 line-clamp-2 text-sm text-ink">
                      {p.product}
                    </p>
                    <p className="mt-3 text-sm font-medium text-ink">
                      {p.price}
                    </p>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* About teaser */}
      <section className="mx-auto max-w-6xl px-6 py-20">
        <div className="grid grid-cols-1 items-center gap-10 md:grid-cols-2">
          <div className="relative aspect-[4/5] w-full overflow-hidden rounded-[2rem] border border-line">
            <Image
              src="/character/cream-sweater-profile-serene.png"
              alt="The Luxe Drawer"
              fill
              sizes="(max-width: 768px) 100vw, 50vw"
              className="object-cover"
            />
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-gold">
              About
            </p>
            <h2 className="font-serif-display mt-2 text-3xl text-ink md:text-4xl">
              Quiet luxury, sourced from Amazon.
            </h2>
            <p className="mt-5 text-base leading-relaxed text-muted">
              The Luxe Drawer is a personal edit. We surface the under-the-radar
              products women keep in their actual cabinets — Japanese skincare,
              French fragrance, fashion staples — and link straight to Amazon.
              No pop-ups, no inventory. Just a small list, kept honest.
            </p>
            <Link
              href="/about"
              className="mt-7 inline-flex items-center text-sm text-ink underline underline-offset-4 hover:text-gold"
            >
              Read more →
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
