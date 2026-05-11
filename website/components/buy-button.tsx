"use client";
import { trackAmazonClick } from "@/lib/analytics/client";

export function BuyButton({
  slug,
  destination,
  className,
  children,
}: {
  slug: string;
  destination: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <a
      href={destination}
      target="_blank"
      rel="nofollow sponsored noopener"
      className={className}
      onClick={() => trackAmazonClick({ slug, destination })}
    >
      {children}
    </a>
  );
}
