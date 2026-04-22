import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = "https://hemerascope.com";

  return [
    { url: base, lastModified: new Date(), changeFrequency: "weekly", priority: 1.0 },
    { url: `${base}/legal/privacy`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.3 },
    { url: `${base}/legal/terms`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.3 },
    { url: `${base}/legal/cookies`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.3 },
    { url: `${base}/legal/security`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.4 },
    { url: `${base}/legal/methodology`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.5 },
    { url: `${base}/legal/sub-processors`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.2 },
    { url: `${base}/legal/modern-slavery`, lastModified: new Date(), changeFrequency: "yearly", priority: 0.2 },
    { url: `${base}/legal/accessibility`, lastModified: new Date(), changeFrequency: "yearly", priority: 0.2 },
  ];
}
