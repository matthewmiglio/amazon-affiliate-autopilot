import type { Metadata } from "next";
import { breadcrumbLd, jsonLd } from "@/lib/seo";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description:
    "Privacy policy for the The Luxe Drawer Uploader application — Pinterest API integration.",
  alternates: { canonical: "/privacy" },
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
            href="mailto:matmigg0804@gmail.com"
            className="underline underline-offset-4 hover:text-gold"
          >
            matmigg0804@gmail.com
          </a>
          ). It accesses Pinterest only on behalf of the account owner
          (theluxedrawer) for the purpose of publishing video pins via the
          Pinterest API v5.
        </p>

        <section>
          <h2 className="font-serif-display text-2xl text-ink">
            Data collected
          </h2>
          <ul className="mt-3 list-disc space-y-2 pl-6 text-muted">
            <li>
              OAuth access tokens issued by Pinterest, stored locally on the
              operator&rsquo;s machine.
            </li>
            <li>
              No data is collected from third parties or end users — there are
              no end users.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="font-serif-display text-2xl text-ink">
            Data sharing
          </h2>
          <p className="mt-3 text-muted">
            None. No data is shared with, sold to, or processed by any third
            party.
          </p>
        </section>

        <section>
          <h2 className="font-serif-display text-2xl text-ink">
            Data retention
          </h2>
          <p className="mt-3 text-muted">
            OAuth tokens are retained until revoked by the user or rotated by
            Pinterest. They can be deleted at any time by removing the local
            token file.
          </p>
        </section>

        <section>
          <h2 className="font-serif-display text-2xl text-ink">User rights</h2>
          <p className="mt-3 text-muted">
            The sole user (the operator) has full control over all stored data
            and may delete it at any time.
          </p>
        </section>

        <section>
          <h2 className="font-serif-display text-2xl text-ink">Contact</h2>
          <p className="mt-3 text-muted">
            <a
              href="mailto:matmigg0804@gmail.com"
              className="underline underline-offset-4 hover:text-gold"
            >
              matmigg0804@gmail.com
            </a>
          </p>
        </section>
      </div>
    </div>
  );
}
