import type { Metadata } from "next";
import { products, uniqueCategories } from "@/lib/products";
import { breadcrumbLd, jsonLd, siteName, siteUrl } from "@/lib/seo";
import ProductsClient from "./products-client";

export const metadata: Metadata = {
  title: "Shop the edit",
  description:
    "Every The Luxe Drawer pick — beauty, fragrance, fashion, and jewelry — sourced from Amazon and curated for the quiet luxury woman.",
  alternates: { canonical: "/products" },
  openGraph: {
    title: "Shop the edit",
    url: `${siteUrl}/products`,
    type: "website",
    images: [`${siteUrl}/opengraph-image`],
  },
  twitter: {
    card: "summary_large_image",
    title: "Shop the edit",
    description:
      "Every The Luxe Drawer pick — beauty, fragrance, fashion, and jewelry — sourced from Amazon and curated for the quiet luxury woman.",
    images: [`${siteUrl}/opengraph-image`],
  },
};

export default function ProductsPage() {
  const categories = uniqueCategories(products);

  const itemListLd = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: `${siteName} — The full edit`,
    numberOfItems: products.length,
    itemListElement: products.map((p, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: `${p.brand} ${p.product}`,
      url: `${siteUrl}/p/${p.slug}`,
      image: `${siteUrl}${p.image}`,
    })),
  };

  const crumbs = breadcrumbLd([
    { name: "Home", path: "/" },
    { name: "Shop the edit", path: "/products" },
  ]);

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={jsonLd([itemListLd, crumbs])}
      />
      <ProductsClient products={products} categories={categories} />
    </>
  );
}
