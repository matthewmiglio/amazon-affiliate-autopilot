export const siteUrl = "https://theluxedrawer.com";
export const siteName = "The Luxe Drawer";
export const siteDescription =
  "The Luxe Drawer curates daily Amazon luxury picks across beauty, fragrance, fashion, and jewelry. The look — without the markup.";
export const ownerEmail = "matmigg0804@gmail.com";

export const socialLinks = {
  youtube: "https://www.youtube.com/@TheLuxeDrawer",
  pinterest: "https://www.pinterest.com/theluxedrawer/",
};

export function jsonLd(data: Record<string, unknown> | Record<string, unknown>[]) {
  return { __html: JSON.stringify(data) };
}

export function breadcrumbLd(
  trail: { name: string; path: string }[],
): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: trail.map((c, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: c.name,
      item: `${siteUrl}${c.path}`,
    })),
  };
}

export const isProductionDeploy =
  !process.env.VERCEL_ENV || process.env.VERCEL_ENV === "production";

export function priceToNumber(raw: string): string | undefined {
  if (!raw) return undefined;
  const m = raw.replace(/,/g, "").match(/(\d+(?:\.\d+)?)/);
  return m ? m[1] : undefined;
}
