import Link from "next/link";
import { FileSearch } from "lucide-react";

import type { HTMLAttributes } from "react";

type LogoProps = HTMLAttributes<HTMLAnchorElement> & {
  href?: string;
  showWordmark?: boolean;
};

export function Logo({ href = "/", showWordmark = true, ...props }: LogoProps) {
  return (
    <Link
      href={href}
      aria-label="NyayaLens home"
      className={`inline-flex items-center gap-2 ${props.className ?? ""}`}
      {...props}
    >
      <span className="flex size-8 items-center justify-center rounded-lg bg-navy text-white">
        <FileSearch className="size-4.5" aria-hidden="true" />
      </span>
      {showWordmark ? (
        <span className="text-lg font-bold tracking-tight text-navy">NyayaLens</span>
      ) : null}
    </Link>
  );
}