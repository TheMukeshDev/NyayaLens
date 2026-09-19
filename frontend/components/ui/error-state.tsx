import { Button } from "./button";

type ErrorStateProps = {
  title?: string;
  message: string;
  retryLabel?: string;
  onRetry?: () => void;
};

/** Standard error state (Screen-Spec §21): calm message, no stack traces. */
export function ErrorState({ title = "Something went wrong", message, retryLabel = "Try again", onRetry }: ErrorStateProps) {
  return (
    <div role="alert" className="flex flex-col items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-6 py-12 text-center">
      <h3 className="text-base font-semibold text-danger-strong">{title}</h3>
      <p className="max-w-md text-sm text-danger-strong">{message}</p>
      {onRetry ? (
        <Button variant="danger-outline" onClick={onRetry} className="mt-3">
          {retryLabel}
        </Button>
      ) : null}
    </div>
  );
}