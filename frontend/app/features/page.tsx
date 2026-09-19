import {
  AlertTriangle,
  BookOpenText,
  FileText,
  ListChecks,
  MessageSquare,
  Scale,
  ShieldCheck,
} from "lucide-react";

import { MarketingLayout } from "@/components/marketing/marketing-layout";
import { Button } from "@/components/ui/button";

const FEATURES = [
  {
    icon: FileText,
    title: "Secure document upload",
    description:
      "Upload PDF, DOCX, JPG or PNG files up to 20 MB. Every file is checked for safety, hashed, and stored privately under your account.",
  },
  {
    icon: BookOpenText,
    title: "Plain-language summary",
    description:
      "A clear overview of the document's purpose, the parties involved, key terms, obligations, and conditions that matter — written for a human, not a lawyer.",
  },
  {
    icon: Scale,
    title: "Clause-by-clause analysis",
    description:
      "Every important clause is explained in plain language, with the original text and page reference shown alongside so you can always verify.",
  },
  {
    icon: AlertTriangle,
    title: "Attention items",
    description:
      "Areas worth reviewing carefully before you decide are called out with clear explanations and practical recommendations.",
  },
  {
    icon: MessageSquare,
    title: "Evidence-grounded Q&A",
    description:
      "Ask anything about your document. Answers cite the exact sections they rely on, and when the document doesn't have enough evidence, NyayaLens says so clearly.",
  },
  {
    icon: ListChecks,
    title: "Action center",
    description:
      "A practical checklist of next steps, follow-ups and important dates you can work through — plus questions to put to a qualified professional.",
  },
  {
    icon: Scale,
    title: "Compare documents",
    description:
      "See exactly what changed between two versions of a document, with before-and-after text and explanations for each change.",
  },
  {
    icon: ShieldCheck,
    title: "Shareable reports",
    description:
      "Generate a review report that combines the summary, attention items and your action plan, ready to download and share.",
  },
];

export default function FeaturesPage() {
  return (
    <MarketingLayout>
      <section className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto flex max-w-2xl flex-col items-center gap-4 text-center">
          <h1 className="text-4xl font-bold tracking-tight text-navy">Features</h1>
          <p className="text-lg text-muted">
            Everything you need to understand a legal document, in one private,
            evidence-backed workspace.
          </p>
        </div>
        <div className="mt-12 grid gap-6 sm:grid-cols-2">
          {FEATURES.map((feature) => {
            const Icon = feature.icon;
            return (
              <div
                key={feature.title}
                className="flex flex-col gap-3 rounded-xl border border-line bg-surface p-6"
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
        <div className="mt-12 flex justify-center">
          <Button href="/signup" size="lg">
            Try it free
          </Button>
        </div>
      </section>
    </MarketingLayout>
  );
}