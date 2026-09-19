"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  AlertTriangle,
  BookOpenText,
  ListChecks,
  MessageSquare,
  ScrollText,
  SlidersHorizontal,
} from "lucide-react";

import type { DocumentOut } from "@/lib/types";

const TABS = [
  { slug: "", label: "Overview", icon: SlidersHorizontal },
  { slug: "summary", label: "Summary", icon: BookOpenText },
  { slug: "clauses", label: "Clauses", icon: ScrollText },
  { slug: "attention", label: "Attention", icon: AlertTriangle },
  { slug: "ask", label: "Ask", icon: MessageSquare },
  { slug: "actions", label: "Actions", icon: ListChecks },
];

/** Horizontal document sub-navigation with accessible active state. */
export function DocumentNav({ document }: { document: DocumentOut }) {
  const pathname = usePathname();
  const base = `/documents/${document.id}`;

  return (
    <nav aria-label="Document sections" className="overflow-x-auto">
      <ul className="flex gap-1 border-b border-line">
        {TABS.map((tab) => {
          const href = tab.slug === "" ? base : `${base}/${tab.slug}`;
          const active = tab.slug === "" ? pathname === href : pathname.startsWith(href);
          const Icon = tab.icon;
          return (
            <li key={tab.slug || "overview"}>
              <Link
                href={href}
                aria-current={active ? "page" : undefined}
                className={`flex items-center gap-2 whitespace-nowrap border-b-2 px-3 py-2.5 text-sm font-medium transition-colors ${
                  active
                    ? "border-brand text-brand"
                    : "border-transparent text-muted hover:text-ink"
                }`}
              >
                <Icon className="size-4" aria-hidden="true" />
                {tab.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}