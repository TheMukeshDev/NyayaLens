"use client";

import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  FileText,
  History,
  MessageCircleQuestion,
  RotateCcw,
  ScanText,
  ShieldCheck,
  Sparkles,
  Upload,
} from "lucide-react";
import { useState } from "react";

import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";

const SAMPLE_TEXT =
  "This Agreement shall automatically renew for successive terms of one year each unless either party gives written notice of termination at least ninety (90) days prior to the expiration of the then-current term. The Employer reserves the right to modify compensation structures unilaterally with 14 days notice.";

const ANALYSIS = {
  summary:
    "Auto-renewal kicks in yearly unless cancelled 3 months early. The employer can change your pay with just 2 weeks' notice.",
  risk: "High risk regarding unilateral salary modifications on short notice.",
  question: "Can notice periods for compensation changes be negotiated to 30 days?",
};

type AnalysisState = "idle" | "analyzing" | "complete";

export default function WorkspacePage() {
  const [documentText, setDocumentText] = useState("");
  const [analysisState, setAnalysisState] = useState<AnalysisState>("idle");

  function analyzeDocument() {
    if (!documentText.trim() || analysisState === "analyzing") return;
    setAnalysisState("analyzing");
    window.setTimeout(() => setAnalysisState("complete"), 900);
  }

  function resetWorkspace() {
    setDocumentText("");
    setAnalysisState("idle");
  }

  const canAnalyze = documentText.trim().length > 0;

  return (
    <main className="min-h-screen bg-canvas text-ink">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Logo href="/" />
          <div className="flex items-center gap-3 text-sm text-muted">
            <span className="hidden items-center gap-1.5 sm:flex">
              <ShieldCheck className="size-4 text-success" aria-hidden="true" />
              Private demo workspace
            </span>
            <Button href="/" variant="ghost" size="sm">Exit demo</Button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 lg:py-12">
        <div className="mb-8 flex flex-col justify-between gap-5 md:flex-row md:items-end">
          <div>
            <div className="mb-3 flex items-center gap-2 text-sm font-medium text-brand">
              <Sparkles className="size-4" aria-hidden="true" />
              Document Workspace
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-navy sm:text-4xl">
              See what your contract really says.
            </h1>
            <p className="mt-2 max-w-2xl text-base text-muted">
              Paste a clause below and get a clear first-pass review in seconds.
              This interactive demo uses sample analysis so no document or AI key is required.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted">
            <History className="size-4" aria-hidden="true" />
            <span>New review</span>
            <ChevronRight className="size-3.5" aria-hidden="true" />
            <span className="font-medium text-ink">Contract analysis</span>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <section className="rounded-xl border border-line bg-surface shadow-sm" aria-labelledby="document-heading">
            <div className="flex items-center justify-between border-b border-line px-5 py-4">
              <div className="flex items-center gap-3">
                <div className="flex size-9 items-center justify-center rounded-lg bg-blue-50 text-brand">
                  <FileText className="size-4.5" aria-hidden="true" />
                </div>
                <div>
                  <h2 id="document-heading" className="font-semibold text-navy">Your document</h2>
                  <p className="text-xs text-muted">Paste text or start with a sample clause</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setDocumentText(SAMPLE_TEXT)}
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-brand hover:text-blue-700"
              >
                <ScanText className="size-3.5" aria-hidden="true" />
                Use sample
              </button>
            </div>

            <div className="p-5">
              <label htmlFor="document-text" className="sr-only">Contract text</label>
              <textarea
                id="document-text"
                value={documentText}
                onChange={(event) => {
                  setDocumentText(event.target.value);
                  if (analysisState !== "idle") setAnalysisState("idle");
                }}
                placeholder="Paste an employment agreement, lease clause, or any contract text here..."
                className="min-h-72 w-full resize-y rounded-lg border border-line bg-canvas/50 p-4 text-sm leading-7 text-ink shadow-inner placeholder:text-slate-400 focus:border-brand focus:bg-surface focus:outline-none focus:ring-2 focus:ring-blue-100"
              />
              <div className="mt-3 flex items-center justify-between text-xs text-muted">
                <span>{documentText.length.toLocaleString()} characters</span>
                <span>Plain text · Private by design</span>
              </div>

              <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center">
                <Button
                  type="button"
                  size="lg"
                  loading={analysisState === "analyzing"}
                  disabled={!canAnalyze}
                  onClick={analyzeDocument}
                  className="sm:flex-1"
                >
                  {analysisState === "analyzing" ? "Reading your document..." : "Analyze document"}
                  {analysisState !== "analyzing" ? <Sparkles className="size-4" aria-hidden="true" /> : null}
                </Button>
                {analysisState !== "idle" ? (
                  <button
                    type="button"
                    onClick={resetWorkspace}
                    className="inline-flex h-12 items-center justify-center gap-2 rounded-xl px-4 text-sm font-medium text-muted hover:bg-canvas hover:text-navy"
                  >
                    <RotateCcw className="size-4" aria-hidden="true" />
                    Start over
                  </button>
                ) : null}
              </div>
            </div>

            <div className="border-t border-line bg-canvas/40 px-5 py-4">
              <div className="flex items-center gap-2 text-xs text-muted">
                <Upload className="size-3.5" aria-hidden="true" />
                <span>PDF and DOCX upload available in the full workspace</span>
              </div>
            </div>
          </section>

          <section className="rounded-xl border border-line bg-surface shadow-sm" aria-labelledby="analysis-heading" aria-live="polite">
            <div className="flex items-center justify-between border-b border-line px-5 py-4">
              <div className="flex items-center gap-3">
                <div className="flex size-9 items-center justify-center rounded-lg bg-navy text-white">
                  <Sparkles className="size-4.5" aria-hidden="true" />
                </div>
                <div>
                  <h2 id="analysis-heading" className="font-semibold text-navy">AI analysis</h2>
                  <p className="text-xs text-muted">Grounded review of the submitted text</p>
                </div>
              </div>
              {analysisState === "complete" ? (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-green-50 px-2.5 py-1 text-xs font-medium text-success">
                  <CheckCircle2 className="size-3.5" aria-hidden="true" />
                  Complete
                </span>
              ) : null}
            </div>

            {analysisState === "idle" ? (
              <div className="flex min-h-[27rem] flex-col items-center justify-center px-8 text-center">
                <div className="flex size-14 items-center justify-center rounded-2xl bg-blue-50 text-brand">
                  <MessageCircleQuestion className="size-7" aria-hidden="true" />
                </div>
                <h3 className="mt-5 font-semibold text-navy">Your review will appear here</h3>
                <p className="mt-2 max-w-sm text-sm leading-6 text-muted">
                  Add contract text on the left, then analyze it to see a plain-language summary, risks, and questions to take to a professional.
                </p>
              </div>
            ) : analysisState === "analyzing" ? (
              <div className="flex min-h-[27rem] flex-col justify-center px-8">
                <div className="mx-auto w-full max-w-md">
                  <div className="flex items-center gap-3">
                    <div className="flex size-10 items-center justify-center rounded-full bg-blue-50 text-brand">
                      <Sparkles className="size-5 animate-pulse" aria-hidden="true" />
                    </div>
                    <div>
                      <p className="font-semibold text-navy">Reviewing your clause</p>
                      <p className="text-sm text-muted">Finding terms worth a closer look...</p>
                    </div>
                  </div>
                  <div className="mt-7 h-2 overflow-hidden rounded-full bg-blue-50">
                    <div className="processing-indeterminate h-full rounded-full bg-brand" />
                  </div>
                  <div className="mt-4 grid gap-3 text-xs text-muted sm:grid-cols-3">
                    <span>Reading terms</span><span>Checking risks</span><span>Preparing questions</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-4 p-5">
                <article className="rounded-lg border border-blue-100 bg-blue-50/60 p-5">
                  <div className="flex items-center gap-2 text-sm font-semibold text-brand">
                    <FileText className="size-4" aria-hidden="true" />
                    Plain-language summary
                  </div>
                  <p className="mt-3 text-sm leading-7 text-ink">{ANALYSIS.summary}</p>
                </article>
                <article className="rounded-lg border border-amber-200 bg-amber-50/60 p-5">
                  <div className="flex items-center gap-2 text-sm font-semibold text-warning">
                    <AlertTriangle className="size-4" aria-hidden="true" />
                    Review priorities
                  </div>
                  <p className="mt-3 text-sm leading-7 text-ink">{ANALYSIS.risk}</p>
                  <span className="mt-4 inline-flex rounded-full border border-amber-200 bg-white px-2.5 py-1 text-xs font-semibold text-warning">High priority</span>
                </article>
                <article className="rounded-lg border border-line bg-canvas/50 p-5">
                  <div className="flex items-center gap-2 text-sm font-semibold text-navy">
                    <MessageCircleQuestion className="size-4 text-brand" aria-hidden="true" />
                    Questions for a professional
                  </div>
                  <p className="mt-3 text-sm leading-7 text-ink">“{ANALYSIS.question}”</p>
                </article>
                <p className="px-1 pt-1 text-xs leading-5 text-muted">
                  This is an informational first-pass review, not legal advice. Confirm important decisions with a qualified professional.
                </p>
              </div>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}