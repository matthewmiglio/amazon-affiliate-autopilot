import type { Metadata } from "next";
import { breadcrumbLd, jsonLd, siteUrl } from "@/lib/seo";

const privacyTitle = "Privacy Policy";
const privacyDescription =
  "Privacy policy for The Luxe Drawer Uploader — single-operator publishing tool for YouTube, X, Pinterest, Instagram, and Facebook.";

export const metadata: Metadata = {
  title: privacyTitle,
  description: privacyDescription,
  alternates: { canonical: "/privacy" },
  openGraph: {
    title: privacyTitle,
    description: privacyDescription,
    url: `${siteUrl}/privacy`,
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: privacyTitle,
    description: privacyDescription,
  },
};

export default function PrivacyPage() {
  const crumbs = breadcrumbLd([
    { name: "Home", path: "/" },
    { name: "Privacy Policy", path: "/privacy" },
  ]);
  return (
    <div className="mx-auto max-w-3xl px-6 pb-24 pt-16">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={jsonLd(crumbs)}
      />
      <p className="text-xs uppercase tracking-[0.28em] text-gold">Legal</p>
      <h1 className="font-serif-display mt-2 text-4xl text-ink md:text-5xl">
        Privacy Policy
      </h1>
      <p className="mt-3 text-sm text-muted">
        The Luxe Drawer Uploader · Last updated: 2026-05-08
      </p>

      <div className="mt-10 space-y-8 text-base leading-relaxed text-ink">
        <p>
          This application is for personal use only and is operated by a
          single individual (
          <a
            href="mailto:matthew2miglio0804@gmail.com"
            className="underline underline-offset-4 hover:text-gold"
          >
            matthew2miglio0804@gmail.com
          </a>
          ). It accesses YouTube, X (Twitter), Pinterest, Instagram, and
          Facebook only on behalf of the account owner (theluxedrawer) for the
          sole purpose of publishing the operator&rsquo;s own short-form video
          content to the operator&rsquo;s own accounts on those platforms.
        </p>

        <section>
          <h2 className="font-serif-display text-2xl text-ink">
            Data collected
          </h2>
          <ul className="mt-3 list-disc space-y-2 pl-6 text-muted">
            <li>
              OAuth access tokens and refresh tokens issued by each platform
              (YouTube, X, Pinterest, Instagram, Facebook), stored locally on
              the operator&rsquo;s machine. No tokens for any other user are
              accessed, requested, or stored.
            </li>
            <li>
              Public response metadata returned by the publishing endpoints
              (post ID, post URL, processing status), retained locally to
              de-duplicate uploads and resume after failures.
            </li>
            <li>
              No data is collected from third parties or end users — this
              application has no end users beyond the single operator.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="font-serif-display text-2xl text-ink">
            Data sharing
          </h2>
          <p className="mt-3 text-muted">
            None. No data is shared with, sold to, or processed by any third
            party. Tokens never leave the operator&rsquo;s local machine
            except in outbound API calls to the issuing platform.
          </p>
        </section>

        <section>
          <h2 className="font-serif-display text-2xl text-ink">
            Data retention
          </h2>
          <p className="mt-3 text-muted">
            OAuth tokens are retained until revoked by the operator on the
            issuing platform or rotated by the platform itself. They can be
            deleted at any time by removing the local token file. Upload
            metadata is retained indefinitely on the operator&rsquo;s local
            machine for the lifetime of the project.
          </p>
        </section>

        <section>
          <h2 className="font-serif-display text-2xl text-ink">User rights</h2>
          <p className="mt-3 text-muted">
            The sole user (the operator) has full control over all stored data
            and may delete it at any time. Because there are no third-party
            end users, no external data-rights requests apply.
          </p>
        </section>

        <section>
          <h2 className="font-serif-display text-2xl text-ink">
            Children&rsquo;s privacy
          </h2>
          <p className="mt-3 text-muted">
            This application is not directed at, nor used by, anyone under 18.
            No data from children is collected or processed.
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
