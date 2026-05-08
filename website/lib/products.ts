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
};

export const products: Product[] = productsData as Product[];

export function uniqueCategories(items: Product[]): string[] {
  const set = new Set<string>();
  for (const p of items) {
    if (p.category) set.add(p.category);
  }
  return Array.from(set).sort();
}
