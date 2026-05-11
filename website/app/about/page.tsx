import type { Metadata } from "next";
import Image from "next/image";
import { breadcrumbLd, jsonLd, siteUrl } from "@/lib/seo";

const aboutTitle = "About";
const aboutDescription =
  "The Luxe Drawer is a small, personal edit of Amazon luxury finds for women — beauty, fragrance, fashion, and jewelry.";

export const metadata: Metadata = {
  title: aboutTitle,
  description: aboutDescription,
  alternates: { canonical: "/about" },
  openGraph: {
    title: aboutTitle,
    description: aboutDescription,
    url: `${siteUrl}/about`,
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: aboutTitle,
    description: aboutDescription,
  },
};

export default function AboutPage() {
  const crumbs = breadcrumbLd([
    { name: "Home", path: "/" },
    { name: "About", path: "/about" },
  ]);
  return (
    <div className="mx-auto max-w-5xl px-6 pb-24 pt-16">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={jsonLd(crumbs)}
      />
      <header className="mb-12 max-w-2xl">
        <p className="text-xs uppercase tracking-[0.28em] text-gold">
          Our story
        </p>
        <h1 className="font-serif-display mt-2 text-4xl text-ink md:text-5xl">
          About The Luxe Drawer
        </h1>
      </header>

      <div className="grid grid-cols-1 gap-12 md:grid-cols-5">
        <div className="md:col-span-2">
          <div className="relative aspect-[4/5] w-full overflow-hidden rounded-[2rem] border border-line">
            <Image
              src="/character/cream-sweater-profile-serene.png"
              alt="The Luxe Drawer"
              fill
              sizes="(max-width: 768px) 100vw, 40vw"
              className="object-cover"
            />
          </div>
        </div>
        <div className="prose prose-stone max-w-none md:col-span-3">
          <p className="text-lg leading-relaxed text-ink">
            The Luxe Drawer started as a personal list — a private cabinet of
            the products that quietly do the work. Japanese skincare that
            actually changes a face. French fragrance that doesn't shout. The
            small fashion details that make an outfit feel considered.
          </p>
          <p className="mt-5 leading-relaxed text-muted">
            Almost everything on this list lives on Amazon, which means quick
            shipping, easy returns, and prices that often come in well under
            department-store retail. We share the link, you decide. There's no
            inventory on our side, no upsell — we point to the same listings
            you'd reach yourself.
          </p>
          <p className="mt-5 leading-relaxed text-muted">
            New finds are added regularly across our four pillars: beauty,
            fragrance, fashion, and jewelry. We refresh the edit as products
            sell out, prices change, and new releases land. Follow along on
            Pinterest for the visual edit.
          </p>

          <h2 className="font-serif-display mt-10 text-2xl text-ink">
            Affiliate disclosure
          </h2>
          <p className="mt-3 leading-relaxed text-muted">
            The Luxe Drawer is a participant in the Amazon Services LLC
            Associates Program, an affiliate advertising program. As an Amazon
            Associate we earn from qualifying purchases. We may receive a
            small commission when you click through and buy, at no extra cost
            to you. Our editorial picks are not paid placements — products are
            chosen first, links added second.
          </p>
        </div>
      </div>
    </div>
  );
}
