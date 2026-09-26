import {
  AlertTriangle,
  ArrowRight,
  BookOpenText,
  FileText,
  MessageSquare,
  Scale,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { MarketingLayout } from "@/components/marketing/marketing-layout";
import { Button } from "@/components/ui/button";

const FEATURES = [
  {
    icon: BookOpenText,
    title: "Plain-language summary",
    description: "Understand what a document says — purpose, parties, key terms and obligations — without legalese.",
  },
  {
    icon: Scale,
    title: "Clause-by-clause analysis",
    description: "Read each important clause with a plain explanation and a reference back to the exact text and page.",
  },
  {
    icon: AlertTriangle,
    title: "Attention items",
    description: "Get flagged on the areas worth reviewing carefully before you commit to anything.",
  },
  {
    icon: MessageSquare,
    title: "Ask, don't skim",
    description: "Ask questions about your document and get grounded, citable answers — or a clear statement when there's not enough evidence.",
  },
];

const STEPS = [
  {
    icon: FileText,
    title: "Upload a document",
    description: "Securely share a PDF, DOCX, image or scanned document. Files are checked, then analysed in private.",
  },
  {
    icon: Sparkles,
    title: "Understand it",
    description: "Read the summary, review clauses, inspect attention items, and get evidence-backed answers to your questions.",
  },
  {
    icon: ArrowRight,
    title: "Act with confidence",
    description: "Turn the review into an action checklist, important dates, questions for a professional, and a report to share.",
  },
];

export default function MarketingHomePage() {
  return (
    <MarketingLayout>
      <section className="mx-auto w-full max-w-6xl px-4 py-20 sm:px-6 lg:px-8 lg:py-28">
        <div className="mx-auto flex max-w-3xl flex-col items-center gap-6 text-center">
          <p className="inline-flex items-center gap-2 rounded-full border border-line bg-surface px-4 py-1.5 text-xs font-medium text-muted">
            <ShieldCheck className="size-3.5 text-success" aria-hidden="true" />
            Secure · Private · Transparent
          </p>
          <h1 className="text-4xl font-bold tracking-tight text-navy sm:text-5xl lg:text-6xl">
            Understand any legal document before you sign
          </h1>
          <p className="max-w-2xl text-lg leading-relaxed text-muted">
            NyayaLens turns complex agreements into plain-language summaries,
            clause-by-clause explanations, and a practical action plan — every
            claim backed by a citation you can verify.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <Button href="/workspace" variant="secondary" size="lg">
              Try the live demo
              <Sparkles className="size-4" aria-hidden="true" />
            </Button>
            <Button href="/signup" size="lg">
              Get started free
              <ArrowRight className="size-4" aria-hidden="true" />
            </Button>
            <Button href="/how-it-works" variant="secondary" size="lg">
              See how it works
            </Button>
          </div>
          <p className="text-sm text-muted">
            Free to try · No credit card required · Your data stays yours
          </p>
        </div>
      </section>

      <section
        aria-label="Features"
        className="border-y border-line bg-surface py-16"
      >
        <div className="mx-auto grid w-full max-w-6xl gap-6 px-4 sm:grid-cols-2 sm:px-6 lg:px-8">
          {FEATURES.map((feature) => {
            const Icon = feature.icon;
            return (
              <div
                key={feature.title}
                className="flex flex-col gap-3 rounded-xl border border-line bg-canvas/50 p-6"
              >
                <div className="flex size-10 items-center justify-center rounded-lg bg-blue-50 text-brand">
                  <Icon className="size-5" aria-hidden="true" />
                </div>
                <h2 className="text-lg font-semibold text-navy">{feature.title}</h2>
                <p className="text-sm leading-relaxed text-muted">{feature.description}</p>
              </div>
            );
          })}
        </div>
      </section>

      <section aria-label="How it works" className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto flex max-w-2xl flex-col items-center gap-4 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-navy">
            From upload to decisions in three steps
          </h2>
          <p className="text-muted">
            A guided review that keeps you in control and informed at every stage.
          </p>
        </div>
        <ol className="mt-12 grid gap-6 md:grid-cols-3">
          {STEPS.map((step, index) => {
            const Icon = step.icon;
            return (
              <li
                key={step.title}
                className="relative flex flex-col gap-3 rounded-xl border border-line bg-surface p-6"
              >
                <span
                  aria-hidden="true"
                  className="absolute right-4 top-4 text-4xl font-bold text-slate-500"
                >
                  {index + 1}
                </span>
                <div className="flex size-10 items-center justify-center rounded-lg bg-navy text-white">
                  <Icon className="size-5" aria-hidden="true" />
                </div>
                <h3 className="text-lg font-semibold text-navy">{step.title}</h3>
                <p className="text-sm leading-relaxed text-muted">{step.description}</p>
              </li>
            );
          })}
        </ol>
      </section>

      <section
        aria-label="Get started"
        className="mx-auto w-full max-w-6xl px-4 pb-20 sm:px-6 lg:px-8"
      >
        <div className="flex flex-col items-center gap-6 rounded-2xl bg-navy px-6 py-14 text-center text-white">
          <ShieldCheck className="size-10 text-blue-300" aria-hidden="true" />
          <h2 className="text-3xl font-bold tracking-tight">
            Ready to understand your next contract?
          </h2>
          <p className="max-w-xl text-blue-100">
            Upload your first document and see your review come together in
            minutes. No risk, no jargon — just clarity.
          </p>
          <Button href="/signup" size="lg" className="!bg-white !text-navy hover:!bg-blue-50">
            Get started free
          </Button>
        </div>
      </section>
    </MarketingLayout>
  );
}