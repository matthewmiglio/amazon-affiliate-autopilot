import productsData from "@/public/products.json";

export type Product = {
  slug: string;
  brand: string;
  product: string;
  category: string;
  price: string;
  description: string;
  asin: string;
  affiliateLink: string;
  image: string;
  narrationScript: string;
  productUrl: string;
};

export function relatedProducts(
  all: Product[],
  current: Product,
  limit = 4,
): Product[] {
  const sameCat = all.filter(
    (p) => p.slug !== current.slug && p.category === current.category,
  );
  if (sameCat.length >= limit) {
    // simple deterministic shuffle by slug
    return sameCat.slice(0, limit);
  }
  const rest = all.filter(
    (p) => p.slug !== current.slug && p.category !== current.category,
  );
  return [...sameCat, ...rest].slice(0, limit);
}

export function findProductBySlug(slug: string): Product | undefined {
  return products.find((p) => p.slug === slug);
}

export const products: Product[] = productsData as Product[];

export function uniqueCategories(items: Product[]): string[] {
  const set = new Set<string>();
  for (const p of items) {
    if (p.category) set.add(p.category);
  }
  return Array.from(set).sort();
}
