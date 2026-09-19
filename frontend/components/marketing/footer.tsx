import Link from "next/link";

import { Logo } from "@/components/logo";

const FOOTER_LINKS = [
  { href: "/features", label: "Features" },
  { href: "/how-it-works", label: "How it works" },
  { href: "/security", label: "Security" },
  { href: "/about", label: "About" },
  { href: "/privacy", label: "Privacy" },
];

export function MarketingFooter() {
  return (
    <footer className="border-t border-line bg-surface">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-12 sm:px-6 lg:px-8">
        <div className="flex flex-col justify-between gap-8 md:flex-row">
          <div className="flex max-w-sm flex-col gap-3">
            <Logo />
            <p className="text-sm text-muted">
              Understand. Review. Act. NyayaLens helps you understand legal
              documents with plain-language summary, clause analysis, and
              evidence you can verify.
            </p>
          </div>
          <nav aria-label="Footer" className="grid grid-cols-2 gap-8">
            <ul className="flex flex-col gap-2 text-sm">
              {FOOTER_LINKS.slice(0, 3).map((item) => (
                <li key={item.href}>
                  <Link href={item.href} className="text-muted hover:text-brand">
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
            <ul className="flex flex-col gap-2 text-sm">
              {FOOTER_LINKS.slice(3).map((item) => (
                <li key={item.href}>
                  <Link href={item.href} className="text-muted hover:text-brand">
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </div>
        <div className="flex flex-col gap-3 border-t border-line pt-6 text-xs text-muted">
          <p>
            NyayaLens provides informational analysis of documents. It is not a
            law firm or a substitute for qualified professional legal advice.
          </p>
          <p>© {new Date().getFullYear()} NyayaLens. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}