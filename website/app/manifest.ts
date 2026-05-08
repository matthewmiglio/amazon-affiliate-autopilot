import type { MetadataRoute } from "next";
import { siteName, siteDescription } from "@/lib/seo";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: siteName,
    short_name: "Soft Luxe",
    description: siteDescription,
    start_url: "/",
    display: "standalone",
    background_color: "#fbf7f3",
    theme_color: "#fbf7f3",
    icons: [
      {
        src: "/icon",
        sizes: "any",
        type: "image/png",
      },
    ],
  };
}
