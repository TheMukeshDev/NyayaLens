import {
  FileText,
  ListChecks,
  MessageSquare,
  ScanText,
  Sparkles,
} from "lucide-react";

import { MarketingLayout } from "@/components/marketing/marketing-layout";
import { Button } from "@/components/ui/button";

const STEPS = [
  {
    icon: FileText,
    phase: "1 · Upload",
    title: "Upload your document",
    description:
      "Share a PDF, DOCX, image or scanned document. It is encrypted in transit and at rest, and only your account can see it.",
  },
  {
    icon: ScanText,
    phase: "2 · Process",
    title: "We check, extract and analyse",
    description:
      "Your file is validated and scanned for safety. Text is extracted and the document is analysed into sections, clauses and entities.",
  },
  {
    icon: Sparkles,
    phase: "3 · Understand",
    title: "Read your review",
    description:
      "A plain-language summary, clause explanations, attention items and answers are built — each backed by citations you can check.",
  },
  {
    icon: MessageSquare,
    phase: "4 · Ask",
    title: "Ask questions",
    description:
      "Dig deeper with natural-language questions. Answers are grounded in the document or clearly marked as general information.",
  },
  {
    icon: ListChecks,
    phase: "5 · Act",
    title: "Work through actions",
    description:
      "Turn the review into an action checklist, important dates, questions for a professional, and a report you can download.",
  },
];

export default function HowItWorksPage() {
  return (
    <MarketingLayout>
      <section className="mx-auto w-full max-w-3xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-4 text-center">
          <h1 className="text-4xl font-bold tracking-tight text-navy">How it works</h1>
          <p className="text-lg text-muted">
            From a raw file to a confident decision in five straightforward steps.
          </p>
        </div>
        <ol className="mt-12 flex flex-col gap-6">
          {STEPS.map((step) => {
            const Icon = step.icon;
            return (
              <li
                key={step.title}
                className="flex flex-col gap-3 rounded-xl border border-line bg-surface p-6 sm:flex-row sm:gap-5"
              >
                <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-navy text-white">
                  <Icon className="size-6" aria-hidden="true" />
                </div>
                <div className="flex flex-col gap-1.5">
                  <p className="text-xs font-semibold uppercase tracking-wide text-brand">
                    {step.phase}
                  </p>
                  <h2 className="text-lg font-semibold text-navy">{step.title}</h2>
                  <p className="text-sm leading-relaxed text-muted">{step.description}</p>
                </div>
              </li>
            );
          })}
        </ol>
        <div className="mt-12 flex justify-center">
          <Button href="/signup" size="lg">
            Get started free
          </Button>
        </div>
      </section>
    </MarketingLayout>
  );
}