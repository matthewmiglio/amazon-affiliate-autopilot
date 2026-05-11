import type { Metadata, Viewport } from "next";
import Link from "next/link";
import { Inter, Playfair_Display } from "next/font/google";
import "./globals.css";
import {
  jsonLd,
  siteDescription,
  siteName,
  siteUrl,
  socialLinks,
} from "@/lib/seo";
import { AnalyticsTracker } from "@/components/analytics-tracker";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const playfair = Playfair_Display({
  variable: "--font-playfair",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: `${siteName} — Daily Amazon luxury finds for women`,
    template: `%s · ${siteName}`,
  },
  description: siteDescription,
  metadataBase: new URL(siteUrl),
  alternates: { canonical: "/" },
  openGraph: {
    title: siteName,
    description:
      "Daily Amazon luxury finds for women who want the look without the markup.",
    type: "website",
    url: siteUrl,
    siteName,
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: siteName,
    description: siteDescription,
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: "#f7f1ea",
  width: "device-width",
  initialScale: 1,
};

const organizationLd = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: siteName,
  url: siteUrl,
  description: siteDescription,
  sameAs: [socialLinks.youtube, socialLinks.pinterest],
};

const websiteLd = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: siteName,
  url: siteUrl,
  description: siteDescription,
};

function Nav() {
  return (
    <header className="sticky top-0 z-30 border-b border-line/70 bg-[color:var(--background)]/85 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="group flex items-center gap-2">
          <span className="whitespace-nowrap font-serif-display text-lg tracking-tight text-ink sm:text-2xl">
            The Luxe Drawer
          </span>
        </Link>
        <nav className="flex items-center gap-4 text-xs text-muted sm:gap-7 sm:text-sm">
          <Link className="transition hover:text-ink" href="/">
            Home
          </Link>
          <Link className="transition hover:text-ink" href="/products">
            Shop
          </Link>
          <Link className="transition hover:text-ink" href="/about">
            About
          </Link>
          <Link className="transition hover:text-ink" href="/privacy">
            Privacy
          </Link>
        </nav>
      </div>
    </header>
  );
}

function Footer() {
  return (
    <footer className="mt-24 border-t border-line bg-[color:var(--background)]">
      <div className="mx-auto max-w-6xl px-6 py-12">
        <div className="flex flex-col items-start justify-between gap-6 md:flex-row md:items-center">
          <div>
            <p className="font-serif-display text-xl text-ink">
              The Luxe Drawer
            </p>
            <p className="mt-1 max-w-md text-sm text-muted">
              As an Amazon Associate I earn from qualifying purchases. Prices
              and availability are accurate at the time of publishing and
              subject to change.
            </p>
          </div>
          <nav className="flex flex-wrap gap-6 text-sm text-muted">
            <Link className="hover:text-ink" href="/">
              Home
            </Link>
            <Link className="hover:text-ink" href="/products">
              Shop
            </Link>
            <Link className="hover:text-ink" href="/about">
              About
            </Link>
          </nav>
        </div>
        <p className="mt-10 text-xs text-muted">
          © 2026 The Luxe Drawer. All rights reserved.
        </p>
      </div>
    </footer>
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${playfair.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-[color:var(--background)] text-ink">
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={jsonLd([organizationLd, websiteLd])}
        />
        <Nav />
        <main className="flex-1">{children}</main>
        <Footer />
        <AnalyticsTracker />
      </body>
    </html>
  );
}
