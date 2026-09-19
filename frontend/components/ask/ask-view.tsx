"use client";

import { useState } from "react";
import { MessageSquare, Send } from "lucide-react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Field, FormError, Textarea } from "@/components/ui/field";
import { EvidenceBadge } from "@/components/ui/status";
import { Spinner } from "@/components/ui/spinner";
import { clientJson } from "@/lib/api/client";
import { formatPage } from "@/lib/format";
import type { DocumentOut, QAAnswerOut } from "@/lib/types";

type Message = {
  id: string;
  question: string;
  answer: QAAnswerOut | null;
  loading: boolean;
  error: string | null;
};

const SUGGESTIONS = [
  "What does this document require me to do?",
  "What are the most important obligations under this document?",
  "What happens if I break a condition in this document?",
  "Which sections of this document need my attention before signing?",
];

export function AskView({ document }: { document: DocumentOut }) {
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function ask(rawQuestion: string) {
    const text = rawQuestion.trim();
    if (!text || busy) return;

    setBusy(true);
    const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setMessages((current) => [...current, { id, question: text, answer: null, loading: true, error: null }]);
    setQuestion("");
    setError(null);

    const result = await clientJson<QAAnswerOut>(`/documents/${document.id}/ask`, "POST", {
      question: text,
    });

    setMessages((current) =>
      current.map((message) =>
        message.id === id
          ? {
              ...message,
              loading: false,
              answer: result.ok ? result.data : null,
              error: result.ok ? null : (result.error?.message ?? "Could not get an answer."),
            }
          : message,
      ),
    );
    setBusy(false);
  }

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void ask(question);
  }

  return (
    <div className="flex flex-col gap-5">
      <h2 className="sr-only">Ask about this document</h2>
      <Alert kind="info">
        Answers are grounded in this document wherever possible, and marked as
        general information otherwise. Always verify important points against
        the original text and the cited sources.
      </Alert>

      <form onSubmit={submit} className="flex flex-col gap-3">
        <Field label="Ask about this document" htmlFor="ask-question">
          <Textarea
            id="ask-question"
            rows={3}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="e.g. What happens if I leave within the first year?"
            aria-describedby="ask-hint"
          />
          <span id="ask-hint" className="text-xs text-muted">
            Questions are answered from this document&apos;s text with verifiable citations.
          </span>
        </Field>
        {error ? <FormError message={error} /> : null}
        <div className="flex justify-end">
          <Button type="submit" size="md" disabled={!question.trim()} loading={busy}>
            <Send className="size-4" aria-hidden="true" />
            Ask
          </Button>
        </div>
      </form>

      {messages.length === 0 ? (
        <EmptyState
          icon={MessageSquare}
          title="Ask a question"
          description="Ask anything about this document. You can use a suggestion to get started."
          action={
            <div className="mt-3 flex max-w-xl flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => void ask(suggestion)}
                  className="rounded-full border border-line bg-surface px-3 py-1.5 text-sm text-ink transition-colors hover:border-brand/40 hover:bg-blue-50"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          }
        />
      ) : null}

      <div role="log" aria-live="polite" aria-label="Conversation" className="flex flex-col gap-5">
        {messages.map((message) => (
          <div key={message.id} className="flex flex-col gap-3">
            <div className="flex justify-end">
              <p className="max-w-[85%] rounded-2xl rounded-br-sm bg-navy px-4 py-2.5 text-sm text-white">
                {message.question}
              </p>
            </div>

            {message.loading ? (
              <div className="flex items-center gap-2 rounded-2xl rounded-bl-sm border border-line bg-surface px-4 py-3 text-sm text-muted">
                <Spinner size={16} label="Answering" />
                Searching the document for evidence…</div>
            ) : message.error ? (
              <Alert kind="error">{message.error}</Alert>
            ) : message.answer ? (
              <AnswerBlock answer={message.answer} />
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function AnswerBlock({ answer }: { answer: QAAnswerOut }) {
  return (
    <div className="flex max-w-[92%] flex-col gap-3 rounded-2xl rounded-bl-sm border border-line bg-surface p-4 shadow-sm">
      <EvidenceBadge state={answer.evidence_state} />

      {answer.answer ? (
        <p className="text-[15px] leading-relaxed">{answer.answer}</p>
      ) : (
        <p className="text-sm text-muted">
          {answer.abstention_reason ??
            "We could not find enough evidence in this document to answer confidently. Reword your question or ask a professional."}
        </p>
      )}

      {answer.citations.length > 0 ? (
        <div className="flex flex-col gap-2 border-t border-line pt-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">
            Sources ({answer.citations.length})
          </p>
          {answer.citations.map((citation) => (
            <div key={citation.id} className="rounded-lg bg-canvas/70 px-4 py-3">
              <p className="text-sm font-medium text-navy">
                {citation.section}
                {citation.clause ? ` — ${citation.clause}` : ""}
                {formatPage(citation.page_start, citation.page_end)
                  ? ` · ${formatPage(citation.page_start, citation.page_end)}`
                  : ""}
              </p>
              <blockquote className="mt-1 border-l-2 border-blue-200 pl-3 text-sm italic text-muted">
                {citation.source_text}
              </blockquote>
            </div>
          ))}
        </div>
      ) : null}

      {answer.related_sections.length > 0 ? (
        <p className="text-xs text-muted">
          Related reading: {answer.related_sections.map((section) => section.label).join(", ")}
        </p>
      ) : null}

      {answer.model_name ? (
        <p className="text-[11px] text-muted">Model: {answer.model_name}</p>
      ) : null}
    </div>
  );
}