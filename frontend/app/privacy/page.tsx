import { MarketingLayout } from "@/components/marketing/marketing-layout";

const SECTIONS = [
  {
    title: "Information we collect",
    body: "When you create an account we receive your email address and the minimal profile information needed to operate your account. When you upload a document, we receive the file itself and the metadata we need to process it (such as file type and size). We also collect standard usage and diagnostic data needed to keep the service working.",
  },
  {
    title: "How we use your information",
    body: "Your uploaded documents are used only to produce the analysis you requested — summaries, clause explanations, attention items, answers to your questions, comparisons, action plans and reports. Account information is used to identify you, secure your workspace, and provide support. We do not use your documents for advertising and we do not sell, rent or trade your personal data.",
  },
  {
    title: "How your documents are stored",
    body: "Documents are encrypted in transit and at rest. Files are tied to your account and are not shared with other users. We apply strong access controls and validate uploaded files before processing to protect the service and other users.",
  },
  {
    title: "Automated analysis",
    body: "Analysis features, including question answering, use automated processing of your document's text. Where the document does not contain enough evidence to support an answer, NyayaLens marks the result clearly as ungrounded or abstains rather than guessing. Model and prompt versions are surfaced where available so output is auditable.",
  },
  {
    title: "How we share information",
    body: "We do not share your personal information or documents with third parties except where required to operate the service (for example, hosting or security infrastructure), to comply with the law, or where you explicitly direct us to share something.",
  },
  {
    title: "Data retention",
    body: "We retain your account and documents for as long as your account is active, so your workspace keeps working. You can stop using the service at any time, and we will support deletion of your data in line with applicable law.",
  },
  {
    title: "What we are not",
    body: "NyayaLens provides informational analysis of documents. It is not a law firm, a legal service, or a substitute for qualified professional legal advice. You should not rely on it as the sole basis for a legal decision.",
  },
  {
    title: "Your choices and contact",
    body: "You control access to your account and can sign out at any time. If you have questions about privacy or would like to request data access or deletion, contact us and we will respond promptly.",
  },
];

export default function PrivacyPage() {
  return (
    <MarketingLayout>
      <section className="mx-auto w-full max-w-3xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-3">
          <h1 className="text-4xl font-bold tracking-tight text-navy">Privacy policy</h1>
          <p className="text-muted">
            Last updated: {new Date().toLocaleDateString("en", { year: "numeric", month: "long", day: "numeric" })}
          </p>
        </div>
        <p className="mt-8 text-base leading-relaxed text-ink">
          This policy explains in plain language what NyayaLens collects, how we
          use it, and the choices you have. We keep it short and human because
          we think privacy policies should be readable too.
        </p>
        <div className="mt-10 flex flex-col gap-8">
          {SECTIONS.map((section) => (
            <section key={section.title}>
              <h2 className="text-xl font-semibold text-navy">{section.title}</h2>
              <p className="mt-2 text-[15px] leading-relaxed text-ink">{section.body}</p>
            </section>
          ))}
        </div>
      </section>
    </MarketingLayout>
  );
}