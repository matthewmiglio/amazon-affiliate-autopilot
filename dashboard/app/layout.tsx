import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "The Luxe Drawer — Analytics",
  description: "Internal analytics for theluxedrawer.com",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
