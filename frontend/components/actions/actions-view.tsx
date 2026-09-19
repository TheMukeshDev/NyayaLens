"use client";

import { useState } from "react";
import {
  CalendarClock,
  ListChecks,
  MessageSquareText,
  Sparkles,
} from "lucide-react";

import { ActionCard } from "@/components/actions/action-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Field, FormError, Textarea } from "@/components/ui/field";
import { SkeletonList } from "@/components/ui/skeleton";
import { EvidenceBadge } from "@/components/ui/status";
import { clientJson } from "@/lib/api/client";
import { formatSource } from "@/lib/format";
import type {
  ActionCenterOut,
  ActionOut,
  ActionStatus,
  ActionType,
  DocumentOut,
  ImportantDate,
  ProfessionalQuestion,
  ProfessionalQuestionsOut,
  ReportOut,
} from "@/lib/types";
import { useApiData } from "@/lib/use-api-data";

const FOLLOW_UP_TYPES: ActionType[] = ["FOLLOW_UP", "ASK_PROFESSIONAL"];

function groupActions(actions: ActionOut[]): { checklist: ActionOut[]; followUps: ActionOut[] } {
  const checklist: ActionOut[] = [];
  const followUps: ActionOut[] = [];
  for (const action of actions) {
    if (FOLLOW_UP_TYPES.includes(action.action_type)) {
      followUps.push(action);
    } else {
      checklist.push(action);
    }
  }
  return { checklist, followUps };
}

function DatesCard({ dates }: { dates: ImportantDate[] }) {
  if (dates.length === 0) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CalendarClock className="size-4.5 text-brand" aria-hidden="true" />
          Important dates
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="flex flex-col gap-3">
          {dates.map((date, index) => (
            <li key={index} className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3 last:border-0 last:pb-0">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-navy">{date.normalized ?? date.value}</p>
                {date.label ? <p className="text-sm text-muted">{date.label}</p> : null}
              </div>
              {formatSource(date.source) ? (
                <span className="text-xs text-muted">{formatSource(date.source)}</span>
              ) : null}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

export function ActionsView({ document }: { document: DocumentOut }) {
  const { loading: loadingExisting, data: existing } = useApiData<
    ActionOut[] | { items: ActionOut[] }
  >(`/actions?document_id=${document.id}`);

  const [board, setBoard] = useState<ActionCenterOut | null>(null);
  const [generating, setGenerating] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [questionContext, setQuestionContext] = useState("");
  const [questions, setQuestions] = useState<ProfessionalQuestionsOut | null>(null);
  const [questionsBusy, setQuestionsBusy] = useState(false);
  const [questionError, setQuestionError] = useState<string | null>(null);
  const [reportBusy, setReportBusy] = useState(false);
  const [reportCreated, setReportCreated] = useState<ReportOut | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const existingItems: ActionOut[] = Array.isArray(existing)
    ? existing
    : (existing?.items as ActionOut[] | undefined) ?? [];

  const seeded =
    board ??
    (existingItems.length > 0
      ? {
          document_id: document.id,
          checklist: groupActions(existingItems).checklist,
          follow_ups: groupActions(existingItems).followUps,
          important_dates: [],
          evidence_state: "DOCUMENT-GROUNDED" as const,
          abstention_reason: null,
        }
      : null);

  const checklist = seeded?.checklist ?? [];
  const followUps = seeded?.follow_ups ?? [];

  async function generate() {
    setGenerating(true);
    setActionError(null);
    const result = await clientJson<ActionCenterOut>(
      `/documents/${document.id}/action-center`,
      "POST",
    );
    setGenerating(false);
    if (result.ok && result.data) {
      setBoard(result.data);
    } else {
      setActionError(result.error?.message ?? "Could not generate the action plan.");
    }
  }

  async function setStatus(action: ActionOut, status: ActionStatus) {
    setBusyAction(action.id);
    setActionError(null);
    const result = await clientJson<ActionOut>(`/actions/${action.id}`, "PATCH", { status });
    setBusyAction(null);
    if (!result.ok) {
      setActionError(result.error?.message ?? "Could not update this action.");
      return;
    }
    setBoard((current) => {
      if (!current) return current;
      const patch = (items: ActionOut[]) =>
        items.map((item) => (item.id === action.id ? (result.data as ActionOut) : item));
      return { ...current, checklist: patch(current.checklist), follow_ups: patch(current.follow_ups) };
    });
  }

  async function generateQuestions() {
    setQuestionsBusy(true);
    setQuestionError(null);
    const context = questionContext.trim();
    const result = await clientJson<ProfessionalQuestionsOut>(
      `/documents/${document.id}/questions/generate${context ? `?user_context=${encodeURIComponent(context)}` : ""}`,
      "POST",
    );
    setQuestionsBusy(false);
    if (result.ok && result.data) {
      setQuestions(result.data);
    } else {
      setQuestionError(result.error?.message ?? "Could not generate questions.");
    }
  }

  async function createReport() {
    setReportBusy(true);
    const result = await clientJson<ReportOut>(`/documents/${document.id}/reports`, "POST");
    setReportBusy(false);
    if (result.ok && result.data) {
      setReportCreated(result.data);
    } else {
      setActionError(result.error?.message ?? "Could not create the report.");
    }
  }

  if (loadingExisting && !board) {
    return <SkeletonList rows={4} />;
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-col gap-1">
          <p className="text-sm text-muted">
            Practical next steps from your review — each item traces back to a
            specific part of the document.
          </p>
          {seeded?.evidence_state ? <EvidenceBadge state={seeded.evidence_state} /> : null}
        </div>
        <Button
          variant="secondary"
          onClick={() => void generate()}
          loading={generating}
          disabled={generating}
        >
          <Sparkles className="size-4" aria-hidden="true" />
          {seeded ? "Regenerate action plan" : "Generate action plan"}
        </Button>
      </div>

      {actionError ? <FormError message={actionError} /> : null}

      {!seeded && !generating ? (
        <EmptyState
          icon={ListChecks}
          title="No action plan yet"
          description="Generate an action plan to turn this document's review into a checklist of practical next steps, follow-ups, and important dates."
          action={
            <Button onClick={() => void generate()}>
              <Sparkles className="size-4" aria-hidden="true" />
              Generate action plan
            </Button>
          }
        />
      ) : null}

      {seeded ? (
        <>
          <section aria-labelledby="checklist-heading" className="flex flex-col gap-3">
            <h2 id="checklist-heading" className="text-lg font-semibold tracking-tight text-navy">
              Review checklist
            </h2>
            {checklist.length > 0 ? (
              <div className="flex flex-col gap-3">
                {checklist.map((action) => (
                  <ActionCard
                    key={action.id}
                    action={action}
                    busy={busyAction === action.id}
                    onStatus={(status) => void setStatus(action, status)}
                  />
                ))}
              </div>
            ) : (
              <EmptyState title="Nothing to review" description="No checklist items were generated for this document." />
            )}
          </section>

          <section aria-labelledby="followups-heading" className="flex flex-col gap-3">
            <h2 id="followups-heading" className="text-lg font-semibold tracking-tight text-navy">
              Follow-ups
            </h2>
            {followUps.length > 0 ? (
              <div className="flex flex-col gap-3">
                {followUps.map((action) => (
                  <ActionCard
                    key={action.id}
                    action={action}
                    busy={busyAction === action.id}
                    onStatus={(status) => void setStatus(action, status)}
                  />
                ))}
              </div>
            ) : (
              <EmptyState
                title="No follow-ups"
                description="Items to follow up on, such as documents to collect or facts to verify, will appear here."
              />
            )}
          </section>

          <DatesCard dates={seeded.important_dates ?? []} />

          {/* Questions for a professional */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageSquareText className="size-4.5 text-brand" aria-hidden="true" />
                Questions for a professional
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <p className="text-sm text-muted">
                Generate questions to discuss with a qualified legal professional,
                each traced to a specific part of the document.
              </p>
              <Field label="Anything specific to mention? (optional)" htmlFor="question-context">
                <Textarea
                  id="question-context"
                  rows={2}
                  value={questionContext}
                  onChange={(event) => setQuestionContext(event.target.value)}
                  placeholder="e.g. I'm joining as a contractor and probation applies."
                />
              </Field>
              {questionError ? <FormError message={questionError} /> : null}
              <div>
                <Button
                  variant="secondary"
                  onClick={() => void generateQuestions()}
                  loading={questionsBusy}
                  disabled={questionsBusy}
                >
                  <Sparkles className="size-4" aria-hidden="true" />
                  Generate questions
                </Button>
              </div>
              {questions ? (
                <div className="flex flex-col gap-3">
                  {questions.evidence_state ? <EvidenceBadge state={questions.evidence_state} /> : null}
                  {questions.questions.length > 0 ? (
                    <ol className="list-decimal space-y-2 pl-5">
                      {questions.questions.map((question: ProfessionalQuestion, index) => (
                        <li key={index} className="text-[15px] leading-relaxed">
                          {question.question}
                          {formatSource(question.source) ? (
                            <span className="block text-xs text-muted">
                              Source: {formatSource(question.source)}
                            </span>
                          ) : null}
                        </li>
                      ))}
                    </ol>
                  ) : (
                    <p className="text-sm text-muted">
                      {questions.abstention_reason ??
                        "No questions could be generated for the current context."}
                    </p>
                  )}
                </div>
              ) : null}
            </CardContent>
          </Card>

          {/* Report */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ListChecks className="size-4.5 text-brand" aria-hidden="true" />
                Review report
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <p className="text-sm text-muted">
                Create a downloadable review report that combines the summary, attention
                items, and action plan of this document.
              </p>
              {reportCreated ? (
                <div className="flex flex-col gap-2 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm">
                  <p className="font-medium text-success">Report created</p>
                  <Button href="/reports" size="sm">
                    View reports
                  </Button>
                </div>
              ) : (
                <div>
                  <Button variant="secondary" onClick={() => void createReport()} loading={reportBusy} disabled={reportBusy}>
                    Create review report
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}