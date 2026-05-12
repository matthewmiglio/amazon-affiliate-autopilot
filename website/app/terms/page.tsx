import type { Metadata } from "next";
import { breadcrumbLd, jsonLd, siteUrl } from "@/lib/seo";

const termsTitle = "Terms of Service";
const termsDescription =
  "Terms of service for The Luxe Drawer Uploader — single-operator publishing tool for YouTube, X, Pinterest, Instagram, and Facebook.";

export const metadata: Metadata = {
  title: termsTitle,
  description: termsDescription,
  alternates: { canonical: "/terms" },
  openGraph: {
    title: termsTitle,
    description: termsDescription,
    url: `${siteUrl}/terms`,
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: termsTitle,
    description: termsDescription,
  },
};

export default function TermsPage() {
  const crumbs = breadcrumbLd([
    { name: "Home", path: "/" },
    { name: "Terms of Service", path: "/terms" },
  ]);
  return (
    <div className="mx-auto max-w-3xl px-6 pb-24 pt-16">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={jsonLd(crumbs)}
      />
      <p className="text-xs uppercase tracking-[0.28em] text-gold">Legal</p>
      <h1 className="font-serif-display mt-2 text-4xl text-ink md:text-5xl">
        Terms of Service
      </h1>
      <p className="mt-3 text-sm text-muted">
        The Luxe Drawer Uploader · Last updated: 2026-05-12
      </p>

      <div className="mt-10 space-y-8 text-base leading-relaxed text-ink">
        <p>
          This application (&ldquo;the Service&rdquo;) is operated by a single
          individual (
          <a
            href="mailto:matthew2miglio0804@gmail.com"
            className="underline underline-offset-4 hover:text-gold"
          >
            matthew2miglio0804@gmail.com
          </a>
          ) for the sole purpose of publishing the operator&rsquo;s own
          short-form video content to the operator&rsquo;s own accounts on
          YouTube, X (Twitter), Pinterest, Instagram, and Facebook.
        </p>

        <section>
          <h2 className="font-serif-display text-2xl text-ink">
            Eligible users
          </h2>
          <p className="mt-3 text-muted">
            The Service has exactly one user: the operator. It is not made
            available to third parties, and no accounts may be created on it
            by anyone other than the operator.
          </p>
        </section>

        <section>
          <h2 className="font-serif-display text-2xl text-ink">
            Acceptable use
          </h2>
          <ul className="mt-3 list-disc space-y-2 pl-6 text-muted">
            <li>
              The Service is used only to publish content the operator owns or
              has the right to publish.
            </li>
            <li>
              Every published post is uniquely generated for that post; no
              duplicate, recycled, or scraped third-party content is
              redistributed.
            </li>
            <li>
              Every affiliate post includes the FTC-compliant
              <code className="mx-1 rounded bg-paper px-1.5 py-0.5 text-sm text-ink">
                #ad
              </code>
              disclosure inline.
            </li>
            <li>
              The Service is not used to harass, defame, mislead, or otherwise
              violate the policies of any destination platform.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="font-serif-display text-2xl text-ink">
            Affiliate disclosure
          </h2>
          <p className="mt-3 text-muted">
            Posts published via the Service contain links to Amazon products
            through the Amazon Associates affiliate program. The operator may
            earn a commission on qualifying purchases at no extra cost to the
            buyer. This relationship is disclosed in every post via
            <code className="mx-1 rounded bg-paper px-1.5 py-0.5 text-sm text-ink">
              #ad
            </code>
            and in the bio of every destination account.
          </p>
        </section>

        <section>
          <h2 className="font-serif-display text-2xl text-ink">
            Platform compliance
          </h2>
          <p className="mt-3 text-muted">
            The Service interacts with each destination platform only through
            official, documented APIs and within those platforms&rsquo;
            published rate limits and terms of service. The operator complies
            with each platform&rsquo;s rules on automation, affiliate
            marketing, and content disclosure.
          </p>
        </section>

        <section>
          <h2 className="font-serif-display text-2xl text-ink">
            No warranty
          </h2>
          <p className="mt-3 text-muted">
            The Service is provided as-is, for personal operational use, with
            no warranty of fitness for any external purpose. Outages,
            platform-side rejections, or upstream API failures may interrupt
            publishing at any time.
          </p>
        </section>

        <section>
          <h2 className="font-serif-display text-2xl text-ink">Changes</h2>
          <p className="mt-3 text-muted">
            These terms may be updated as platform requirements evolve. The
            most recent &ldquo;Last updated&rdquo; date at the top of this page
            reflects the latest version.
          </p>
        </section>

        <section>
          <h2 className="font-serif-display text-2xl text-ink">Contact</h2>
          <p className="mt-3 text-muted">
            <a
              href="mailto:matthew2miglio0804@gmail.com"
              className="underline underline-offset-4 hover:text-gold"
            >
              matthew2miglio0804@gmail.com
            </a>
          </p>
        </section>
      </div>
    </div>
  );
}
