#!/usr/bin/env node
// Build-time data pipeline. Walks ../products/*/manifest.json, copies main
// images into website/public/products/<slug>.<ext>, emits public/products.json.
import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const websiteRoot = path.resolve(__dirname, "..");
const productsRoot = path.resolve(websiteRoot, "..", "products");
const publicProductsDir = path.join(websiteRoot, "public", "products");
const outJsonPath = path.join(websiteRoot, "public", "products.json");

async function main() {
  await fs.mkdir(publicProductsDir, { recursive: true });

  let entries;
  try {
    entries = await fs.readdir(productsRoot, { withFileTypes: true });
  } catch (err) {
    // Source /products/ is local-only (gitignored). On Vercel it's absent —
    // keep whatever is already baked into the repo instead of wiping it.
    try {
      await fs.access(outJsonPath);
      console.warn(
        `[generate-products] source dir missing (${productsRoot}); preserving committed ${path.relative(websiteRoot, outJsonPath)}`,
      );
      return;
    } catch {
      console.warn(`[generate-products] products dir missing: ${productsRoot}`);
      await fs.writeFile(outJsonPath, "[]");
      return;
    }
  }

  const records = [];
  const skipped = [];

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const slug = entry.name;
    const manifestPath = path.join(productsRoot, slug, "manifest.json");

    let manifest;
    try {
      const raw = await fs.readFile(manifestPath, "utf8");
      manifest = JSON.parse(raw);
    } catch (err) {
      skipped.push({ slug, reason: `manifest unreadable: ${err.message}` });
      continue;
    }

    const imgRel = manifest["product-pic-path"];
    if (!imgRel) {
      skipped.push({ slug, reason: "no product-pic-path" });
      continue;
    }
    const imgSrc = path.join(productsRoot, slug, imgRel);
    try {
      await fs.access(imgSrc);
    } catch {
      skipped.push({ slug, reason: `image missing on disk: ${imgRel}` });
      continue;
    }

    const ext = path.extname(imgRel).toLowerCase() || ".jpg";
    const destName = `${slug}${ext}`;
    const destPath = path.join(publicProductsDir, destName);
    await fs.copyFile(imgSrc, destPath);

    // Prefer the cached transparent PNG if it exists.
    const nobgPath = path.join(websiteRoot, "public", "products-nobg", `${slug}.png`);
    let imagePublicPath = `/products/${destName}`;
    try {
      await fs.access(nobgPath);
      imagePublicPath = `/products-nobg/${slug}.png`;
    } catch {
      // fall back to the original
    }

    const aux = manifest["item-auxiliary-information"] || {};
    records.push({
      slug,
      brand: aux.brand || "",
      product: aux.product || slug,
      category: aux.category || "beauty",
      price: (aux.price || "").replace(/\.{2,}/g, "."),
      description: aux.description || "",
      asin: aux.asin || "",
      affiliateLink: aux["affiliate-link"] || "",
      productUrl: aux["product-page-url"] || "",
      image: imagePublicPath,
      narrationScript: manifest["script-raw-text"] || "",
    });
  }

  records.sort((a, b) =>
    (a.brand + a.product).localeCompare(b.brand + b.product),
  );

  await fs.writeFile(outJsonPath, JSON.stringify(records, null, 2));

  console.log(
    `[generate-products] wrote ${records.length} products to ${path.relative(
      websiteRoot,
      outJsonPath,
    )}`,
  );
  if (skipped.length) {
    console.warn(`[generate-products] skipped ${skipped.length}:`);
    for (const s of skipped) console.warn(`  - ${s.slug}: ${s.reason}`);
  }
}

main().catch((err) => {
  console.error("[generate-products] fatal:", err);
  process.exit(1);
});
