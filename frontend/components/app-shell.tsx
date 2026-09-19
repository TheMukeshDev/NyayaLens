"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import {
  FilePlus2,
  FileText,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Menu,
  Scale,
  Settings,
  X,
} from "lucide-react";

import { Logo } from "@/components/logo";
import { signOut } from "@/app/(app)/actions";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/upload", label: "Upload", icon: FilePlus2 },
  { href: "/compare", label: "Compare", icon: Scale },
  { href: "/actions", label: "Actions", icon: ListChecks },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/settings", label: "Settings", icon: Settings },
];

function NavList({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <ul className="flex flex-col gap-1">
      {NAV_ITEMS.map((item) => {
        const active =
          pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(`${item.href}/`));
        const Icon = item.icon;
        return (
          <li key={item.href}>
            <Link
              href={item.href}
              aria-current={active ? "page" : undefined}
              onClick={onNavigate}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                active
                  ? "bg-blue-50 text-brand"
                  : "text-navy hover:bg-canvas hover:text-ink"
              }`}
            >
              <Icon className="size-4.5 shrink-0" aria-hidden="true" />
              {item.label}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

export function AppShell({ email, children }: { email: string | null; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const drawerRef = useRef<HTMLDivElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  // Move focus into the drawer, trap Tab, support Escape, then restore focus.
  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement;
    const menuButton = menuButtonRef.current;
    drawerRef.current?.querySelector<HTMLElement>(FOCUSABLE)?.focus();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpen(false);
        return;
      }
      if (event.key !== "Tab" || !drawerRef.current) return;
      const focusables = drawerRef.current.querySelectorAll<HTMLElement>(FOCUSABLE);
      if (focusables.length === 0) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
      if (previouslyFocused instanceof HTMLElement && document.contains(previouslyFocused)) {
        previouslyFocused.focus();
      } else {
        menuButton?.focus();
      }
    };
  }, [open]);

  return (
    <div className="min-h-screen">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-navy focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-white"
      >
        Skip to main content
      </a>

      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-line bg-surface lg:flex">
        <div className="border-b border-line p-4">
          <Logo />
        </div>
        <nav aria-label="Workspace" className="flex-1 overflow-y-auto p-3">
          <NavList />
        </nav>
        <div className="border-t border-line p-4">
          <p className="truncate text-sm text-muted" title={email ?? ""}>
            {email ?? "Signed in"}
          </p>
          <form action={signOut} className="mt-2">
            <button
              type="submit"
              className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted transition-colors hover:bg-canvas hover:text-navy"
            >
              <LogOut className="size-4.5" aria-hidden="true" />
              Sign out
            </button>
          </form>
        </div>
      </aside>

      {/* Mobile header */}
      <header className="sticky top-0 z-40 flex h-16 items-center justify-between border-b border-line bg-surface px-4 lg:hidden">
        <Logo showWordmark={false} className="!text-navy" />
        <span className="absolute left-1/2 -translate-x-1/2 text-lg font-bold tracking-tight text-navy">
          NyayaLens
        </span>
        <button
          ref={menuButtonRef}
          type="button"
          className="inline-flex size-10 items-center justify-center rounded-lg text-ink hover:bg-canvas"
          aria-expanded={open}
          aria-controls="app-mobile-menu"
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen((value) => !value)}
        >
          {open ? <X className="size-5" aria-hidden="true" /> : <Menu className="size-5" aria-hidden="true" />}
        </button>
      </header>

      {/* Mobile drawer */}
      {open ? (
        <div className="fixed inset-x-0 top-16 bottom-0 z-30 lg:hidden">
          <div
            className="absolute inset-0 bg-navy/40"
            aria-hidden="true"
            onClick={() => setOpen(false)}
          />
          <div
            ref={drawerRef}
            id="app-mobile-menu"
            role="dialog"
            aria-modal="true"
            aria-label="Workspace menu"
            tabIndex={-1}
            className="absolute inset-y-0 left-0 w-72 overflow-y-auto bg-surface p-4 shadow-xl outline-none"
          >
            <nav aria-label="Workspace menu">
              <NavList onNavigate={() => setOpen(false)} />
            </nav>
            <div className="mt-4 border-t border-line pt-4">
              <p className="truncate text-sm text-muted" title={email ?? ""}>
                {email ?? "Signed in"}
              </p>
              <form action={signOut} className="mt-2">
                <button
                  type="submit"
                  className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted transition-colors hover:bg-canvas hover:text-navy"
                >
                  <LogOut className="size-4.5" aria-hidden="true" />
                  Sign out
                </button>
              </form>
            </div>
          </div>
        </div>
      ) : null}

      <div className="lg:pl-64">
        <main id="main-content" className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}