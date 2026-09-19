import {
  Database,
  EyeOff,
  Fingerprint,
  Lock,
  ShieldCheck,
  UserRound,
} from "lucide-react";

import { MarketingLayout } from "@/components/marketing/marketing-layout";

const PILLARS = [
  {
    icon: Lock,
    title: "Encrypted in transit and at rest",
    description:
      "Your documents are protected with transport encryption while moving and strong encryption while stored. Files are never readable by anyone other than you.",
  },
  {
    icon: UserRound,
    title: "Private by design",
    description:
      "Documents are tied to your account and never shared with other users. Your workspace is visible only to you.",
  },
  {
    icon: EyeOff,
    title: "No selling your data",
    description:
      "We do not sell, rent or trade your data for advertising. Your documents exist to help you, and only you.",
  },
  {
    icon: Fingerprint,
    title: "Verified file integrity",
    description:
      "Every upload is hashed and validated, and every claim made about your document points back to the exact source text you can verify yourself.",
  },
  {
    icon: Database,
    title: "Safe file handling",
    description:
      "Files are scanned and validated before processing, and unsupported or unsafe files are rejected before any analysis happens.",
  },
  {
    icon: ShieldCheck,
    title: "Access you can revoke",
    description:
      "Authentication is handled by a trusted provider and governed by your account. You are in control of access to your own data.",
  },
];

export default function SecurityPage() {
  return (
    <MarketingLayout>
      <section className="mx-auto w-full max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center gap-4 text-center">
          <h1 className="text-4xl font-bold tracking-tight text-navy">Security & privacy</h1>
          <p className="max-w-2xl text-lg text-muted">
            Your documents are sensitive, and we treat them that way. Security,
            privacy and transparency are built into every layer.
          </p>
        </div>
        <div className="mt-12 grid gap-6 sm:grid-cols-2">
          {PILLARS.map((pillar) => {
            const Icon = pillar.icon;
            return (
              <div
                key={pillar.title}
                className="flex flex-col gap-3 rounded-xl border border-line bg-surface p-6"
              >
                <div className="flex size-10 items-center justify-center rounded-lg bg-blue-50 text-brand">
                  <Icon className="size-5" aria-hidden="true" />
                </div>
                <h2 className="text-lg font-semibold text-navy">{pillar.title}</h2>
                <p className="text-sm leading-relaxed text-muted">{pillar.description}</p>
              </div>
            );
          })}
        </div>
        <p className="mt-12 rounded-xl border border-line bg-canvas/60 p-6 text-sm leading-relaxed text-muted">
          NyayaLens is not a legal service provider. It provides informational
          analysis to help you understand documents; it does not replace advice
          from a qualified legal professional. See the{" "}
          <a href="/privacy" className="font-medium text-brand underline underline-offset-2 hover:no-underline">
            Privacy policy
          </a>{" "}
          for details.
        </p>
      </section>
    </MarketingLayout>
  );
}