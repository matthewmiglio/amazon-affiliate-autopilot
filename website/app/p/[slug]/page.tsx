import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  findProductBySlug,
  products,
  relatedProducts,
} from "@/lib/products";
import { BuyButton } from "@/components/buy-button";
import {
  breadcrumbLd,
  jsonLd,
  priceToNumber,
  siteName,
  siteUrl,
} from "@/lib/seo";

export function generateStaticParams() {
  return products.map((p) => ({ slug: p.slug }));
}

function metaDescription(p: { narrationScript: string; description: string }) {
  const src = (p.narrationScript || p.description || "").replace(/\s+/g, " ").trim();
  if (!src) return "Curated Amazon find.";
  if (src.length <= 155) return src;
  return src.slice(0, 152).trimEnd() + "...";
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const p = findProductBySlug(slug);
  if (!p) return { title: "Not found" };
  const title = `${p.brand ? p.brand + " " : ""}${p.product}`.trim();
  const desc = metaDescription(p);
  const absImage = `${siteUrl}${p.image}`;
  return {
    title: `${title} | ${siteName}`,
    description: desc,
    alternates: { canonical: `/p/${p.slug}` },
    openGraph: {
      title: `${title} | ${siteName}`,
      description: desc,
      type: "website",
      url: `${siteUrl}/p/${p.slug}`,
      images: [{ url: absImage, width: 1200, height: 1200, alt: title }],
    },
    twitter: {
      card: "summary_large_image",
      title: `${title} | ${siteName}`,
      description: desc,
      images: [absImage],
    },
  };
}

export default async function ProductDetail({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const p = findProductBySlug(slug);
  if (!p) notFound();

  const title = `${p.brand ? p.brand + " " : ""}${p.product}`.trim();
  const related = relatedProducts(products, p, 4);
  const priceNum = priceToNumber(p.price);

  const productLd: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: title,
    image: [`${siteUrl}${p.image}`],
    description: metaDescription(p),
    sku: p.asin || p.slug,
    brand: p.brand ? { "@type": "Brand", name: p.brand } : undefined,
    offers: {
      "@type": "Offer",
      url: p.affiliateLink,
      priceCurrency: "USD",
      price: priceNum || undefined,
      availability: "https://schema.org/InStock",
    },
  };

  const crumbs = breadcrumbLd([
    { name: "Home", path: "/" },
    { name: "Shop the edit", path: "/products" },
    { name: title, path: `/p/${p.slug}` },
  ]);

  // Render narration as paragraphs (split on blank lines or sentence groups).
  const paragraphs = (p.narrationScript || "")
    .split(/\n\s*\n/)
    .map((s) => s.trim())
    .filter(Boolean);

  return (
    <div className="mx-auto max-w-6xl px-6 pb-24 pt-12">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={jsonLd([productLd, crumbs])}
      />

      <nav className="mb-8 text-xs uppercase tracking-[0.18em] text-muted">
        <Link href="/" className="hover:text-ink">
          Home
        </Link>
        <span className="mx-2 text-gold">·</span>
        <Link href="/products" className="hover:text-ink">
          Shop the edit
        </Link>
      </nav>

      <div className="grid grid-cols-1 gap-12 md:grid-cols-12">
        {/* Image */}
        <div className="md:col-span-6">
          <div className="relative aspect-square w-full overflow-hidden rounded-[2rem] border border-line bg-white">
            <Image
              src={p.image}
              alt={title}
              fill
              sizes="(max-width: 768px) 100vw, 50vw"
              className="object-contain p-8"
              priority
            />
          </div>
        </div>

        {/* Detail */}
        <div className="md:col-span-6">
          {p.brand && (
            <p className="text-xs uppercase tracking-[0.28em] text-gold">
              {p.brand}
            </p>
          )}
          <h1 className="font-serif-display mt-3 text-3xl leading-tight text-ink md:text-4xl">
            {p.product}
          </h1>

          {p.price && (
            <p className="mt-5 text-lg font-medium text-ink">{p.price}</p>
          )}

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <BuyButton
              slug={p.slug}
              destination={p.affiliateLink}
              className="inline-flex items-center justify-center rounded-full bg-ink px-8 py-3 text-sm font-medium tracking-wide text-[color:var(--background)] transition hover:bg-[#3a3330]"
            >
              Buy on Amazon →
            </BuyButton>
            <Link
              href="/products"
              className="inline-flex items-center justify-center rounded-full border border-line px-7 py-3 text-sm font-medium text-ink transition hover:border-ink"
            >
              Back to the edit
            </Link>
          </div>

          <p className="mt-6 text-xs leading-relaxed text-muted">
            As an Amazon Associate {siteName} earns from qualifying purchases.
            Pricing and availability are accurate at the time of publishing and
            subject to change.
          </p>

          {paragraphs.length > 0 && (
            <div className="mt-10 space-y-5 border-t border-line/70 pt-8">
              {paragraphs.map((para, i) => (
                <p
                  key={i}
                  className="text-base leading-relaxed text-ink"
                >
                  {para}
                </p>
              ))}
            </div>
          )}

          {p.description && p.description !== p.narrationScript && (
            <details className="mt-8 border-t border-line/70 pt-6">
              <summary className="cursor-pointer text-xs uppercase tracking-[0.18em] text-muted hover:text-ink">
                Product details
              </summary>
              <div className="mt-4 whitespace-pre-line text-sm leading-relaxed text-muted">
                {p.description}
              </div>
            </details>
          )}
        </div>
      </div>

      {/* Related */}
      {related.length > 0 && (
        <section className="mt-24 border-t border-line pt-16">
          <div className="mb-10 flex items-end justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-gold">
                Keep looking
              </p>
              <h2 className="font-serif-display mt-2 text-2xl text-ink md:text-3xl">
                You may also like
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
            {related.map((r) => (
              <li
                key={r.slug}
                className="group overflow-hidden rounded-2xl border border-line bg-[color:var(--background)] transition hover:shadow-md"
              >
                <Link href={`/p/${r.slug}`} className="block">
                  <div className="relative aspect-square overflow-hidden bg-white">
                    <Image
                      src={r.image}
                      alt={`${r.brand} ${r.product}`}
                      fill
                      sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 25vw"
                      className="object-contain p-5 transition duration-500 group-hover:scale-[1.03]"
                    />
                  </div>
                  <div className="p-5">
                    <p className="text-xs uppercase tracking-wider text-gold">
                      {r.brand}
                    </p>
                    <p className="mt-1 line-clamp-2 text-sm text-ink">
                      {r.product}
                    </p>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
