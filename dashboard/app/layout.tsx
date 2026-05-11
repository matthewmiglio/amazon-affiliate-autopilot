import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "The Luxe Drawer — Analytics",
  description: "Internal analytics for theluxedrawer.com",
  robots: { index: false, follow: false },
};

const NAV = [
  { href: "/",          label: "Overview" },
  { href: "/products",  label: "Top products" },
  { href: "/referrers", label: "Referrers" },
  { href: "/geo",       label: "Geo" },
];

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">
        <header className="border-b border-[var(--border)] px-6 py-4 flex items-center gap-6">
          <Link href="/" className="text-lg font-semibold tracking-tight text-[var(--accent)]">
            Luxe Drawer · Analytics
          </Link>
          <nav className="flex gap-4 text-sm text-[var(--muted)]">
            {NAV.map(n => (
              <Link key={n.href} href={n.href} className="hover:text-[var(--fg)] transition-colors">
                {n.label}
              </Link>
            ))}
          </nav>
        </header>
        <main className="flex-1 px-6 py-8 max-w-7xl w-full mx-auto">{children}</main>
      </body>
    </html>
  );
}
