import { Children, cloneElement, forwardRef, isValidElement } from "react";
import type {
  InputHTMLAttributes,
  LabelHTMLAttributes,
  ReactElement,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";

const fieldClasses =
  "w-full rounded-lg border border-line bg-surface px-3 py-2 text-[15px] text-ink placeholder:text-muted disabled:cursor-not-allowed disabled:bg-canvas disabled:text-muted";

export const Label = forwardRef<HTMLLabelElement, LabelHTMLAttributes<HTMLLabelElement>>(
  function Label({ className, ...props }, ref) {
    return (
      <label
        ref={ref}
        className={`flex flex-col gap-1.5 text-sm font-medium text-ink ${className ?? ""}`}
        {...props}
      />
    );
  },
);

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return <input ref={ref} className={`${fieldClasses} ${className ?? ""}`} {...props} />;
  },
);

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement>
>(function Textarea({ className, ...props }, ref) {
  return (
    <textarea
      ref={ref}
      className={`${fieldClasses} min-h-24 resize-y ${className ?? ""}`}
      {...props}
    />
  );
});

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className, children, ...props }, ref) {
    return (
      <select ref={ref} className={`${fieldClasses} ${className ?? ""}`} {...props}>
        {children}
      </select>
    );
  },
);

type FieldProps = {
  label: string;
  htmlFor?: string;
  hint?: string;
  error?: string | null;
  required?: boolean;
  children: ReactNode;
};

/** Form field with visible label, optional hint, and accessible error text. */
export function Field({ label, htmlFor, hint, error, required, children }: FieldProps) {
  const labelId = htmlFor ? `${htmlFor}-label` : undefined;
  const errorId = htmlFor && error ? `${htmlFor}-error` : undefined;
  const hintId = htmlFor && hint ? `${htmlFor}-hint` : undefined;

  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  // Associate hint/error text with the control so assistive tech announces it
  // (WCAG 1.3.1, 3.3.1) and mark the control invalid when an error is present.
  const controls = Children.map(children, (child) => {
    if (!isValidElement(child)) return child;
    if (child.type !== Input && child.type !== Select && child.type !== Textarea) {
      return child;
    }
    const props = child.props as { "aria-describedby"?: string };
    const ids = [props["aria-describedby"], describedBy].filter(Boolean).join(" ") || undefined;
    return cloneElement(child as ReactElement<Record<string, unknown>>, {
      "aria-describedby": ids,
      "aria-invalid": error ? true : undefined,
    });
  });

  return (
    <div className="flex flex-col gap-1.5">
      <label
        id={labelId}
        htmlFor={htmlFor}
        className="text-sm font-medium text-ink"
      >
        {label}
        {required ? (
          <span className="ml-0.5 text-danger-strong" aria-hidden="true">
            *
          </span>
        ) : null}
      </label>
      {controls}
      {hint ? (
        <p id={hintId} className="text-xs text-muted">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} role="alert" className="text-sm text-danger-strong">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function FormError({ id, message }: { id?: string; message: string }) {
  return (
    <p id={id} role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-danger-strong">
      {message}
    </p>
  );
}