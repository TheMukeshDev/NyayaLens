import { BookOpenText, Eye, Scale, ShieldCheck, Sparkles } from "lucide-react";

import { MarketingLayout } from "@/components/marketing/marketing-layout";
import { Button } from "@/components/ui/button";

const VALUES = [
  {
    icon: Eye,
    title: "Transparency over opacity",
    description:
      "Every insight NyayaLens produces is traceable. If you can't verify a claim, we flag it as ungrounded rather than guessing.",
  },
  {
    icon: Scale,
    title: "Understand before you sign",
    description:
      "Legal documents should not be a black box. We make them readable so you can make decisions from understanding, not pressure.",
  },
  {
    icon: ShieldCheck,
    title: "Privacy as a default",
    description:
      "Your documents are yours. Privacy and security are design principles, not afterthoughts.",
  },
  {
    icon: Sparkles,
    title: "Design that respects people",
    description:
      "Calm, clear and supportive interfaces. We design for real people at stressful moments, not for engagement metrics.",
  },
];

export default function AboutPage() {
  return (
    <MarketingLayout>
      <section className="mx-auto w-full max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="flex size-14 items-center justify-center rounded-2xl bg-navy text-white">
            <BookOpenText className="size-7" aria-hidden="true" />
          </div>
          <h1 className="text-4xl font-bold tracking-tight text-navy">About NyayaLens</h1>
        </div>

        <div className="mt-10 flex flex-col gap-6 text-base leading-relaxed text-ink">
          <p>
            Signing a rental agreement, an employment contract, or a loan should
            feel understood, not overwhelming. Yet most people sign legal
            documents every day without fully grasping what they agree to.
          </p>
          <p>
            NyayaLens exists to change that. It turns dense legal documents into
            plain-language summaries, clause-by-clause explanations and practical
            action plans — grounded in the actual text, with every claim
            traceable to a source you can check yourself.
          </p>
          <p>
            We believe technology should expand understanding, not hide behind
            it. NyayaLens is designed to be clear, calm and <em>honest</em> —
            including when it does not know something.
          </p>
          <p>
            NyayaLens is a tool for understanding, not a substitute for a
            qualified legal professional. When something matters, we will tell
            you it is worth asking a professional — and help you prepare for
            that conversation.
          </p>
        </div>

        <h2 className="mt-14 text-2xl font-bold tracking-tight text-navy">What we stand for</h2>
        <div className="mt-8 grid gap-6 sm:grid-cols-2">
          {VALUES.map((value) => {
            const Icon = value.icon;
            return (
              <div
                key={value.title}
                className="flex flex-col gap-3 rounded-xl border border-line bg-surface p-6"
              >
                <div className="flex size-10 items-center justify-center rounded-lg bg-blue-50 text-brand">
                  <Icon className="size-5" aria-hidden="true" />
                </div>
                <h3 className="text-lg font-semibold text-navy">{value.title}</h3>
                <p className="text-sm leading-relaxed text-muted">{value.description}</p>
              </div>
            );
          })}
        </div>

        <div className="mt-12 flex justify-center">
          <Button href="/signup" size="lg">
            Try NyayaLens
          </Button>
        </div>
      </section>
    </MarketingLayout>
  );
}