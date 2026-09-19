"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { CheckCircle2, UploadCloud } from "lucide-react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { clientApi } from "@/lib/api/client";
import { ERROR_MESSAGES } from "@/lib/constants";
import { formatBytes } from "@/lib/format";
import type { DocumentOut } from "@/lib/types";

const MAX_UPLOAD_SIZE_MB = 20;
const MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024;
const ACCEPTED_EXTENSIONS: Record<string, string> = {
  pdf: "PDF",
  docx: "DOCX",
  jpg: "JPG",
  jpeg: "JPEG",
  png: "PNG",
};
const ACCEPT = Object.keys(ACCEPTED_EXTENSIONS)
  .map((ext) => `.${ext}`)
  .join(",");

function isAcceptedFile(name: string): boolean {
  const extension = name.toLowerCase().split(".").pop();
  return extension !== undefined && extension in ACCEPTED_EXTENSIONS;
}

export function UploadForm() {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploaded, setUploaded] = useState<DocumentOut | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function selectFile(candidate: File | null | undefined) {
    if (!candidate) return;
    setUploaded(null);
    setError(null);

    if (!isAcceptedFile(candidate.name)) {
      setFile(null);
      setError("Unsupported file type. Supported types are PDF, DOCX, JPG, and PNG.");
      return;
    }
    if (candidate.size > MAX_UPLOAD_SIZE_BYTES) {
      setFile(null);
      setError(`The file exceeds the maximum allowed size of ${MAX_UPLOAD_SIZE_MB} MB.`);
      return;
    }

    setFile(candidate);
  }

  function reset() {
    setFile(null);
    setUploaded(null);
    setError(null);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || uploading) return;

    setError(null);
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    const result = await clientApi<{ document: DocumentOut }>("/documents", {
      method: "POST",
      body: formData,
    });

    if (result.ok && result.data?.document) {
      setFile(null);
      setUploaded(result.data.document);
    } else {
      const message = result.error?.code
        ? (ERROR_MESSAGES[result.error.code] ?? result.error.message)
        : result.error?.message;
      setError(message ?? "Upload failed. Please try again.");
    }
    setUploading(false);
  }

  return (
    <>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <label
            htmlFor="document-file"
            onDragOver={(event) => {
              event.preventDefault();
              if (!uploading) setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragActive(false);
              selectFile(event.dataTransfer.files?.[0]);
            }}
            className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-12 text-center transition-colors focus-within:ring-2 focus-within:ring-brand focus-within:ring-offset-2 ${
              dragActive ? "border-brand bg-blue-50" : "border-line bg-surface hover:border-brand"
            }`}
          >
            <input
              ref={inputRef}
              id="document-file"
              type="file"
              accept={ACCEPT}
              disabled={uploading}
              aria-describedby="document-file-help"
              aria-invalid={error ? true : undefined}
              onChange={(event) => selectFile(event.target.files?.[0])}
              className="sr-only"
            />
            <UploadCloud className="size-8 text-brand" aria-hidden="true" />
            <span className="text-base font-medium text-ink">
              Drag and drop your document here, or{" "}
              <span className="text-brand underline underline-offset-4">browse files</span>
            </span>
            <span id="document-file-help" className="text-sm text-muted">
              PDF, DOCX, JPG, PNG — up to {MAX_UPLOAD_SIZE_MB} MB
            </span>
          </label>
          <p className="text-xs text-muted">
            Select the file and the button below. Or use the drop zone above.
          </p>
        </div>

        {file ? (
          <div className="flex items-center justify-between gap-4 rounded-lg border border-line bg-surface px-4 py-3">
            <span className="truncate text-sm">{file.name}</span>
            <span className="shrink-0 text-xs text-muted">{formatBytes(file.size)}</span>
          </div>
        ) : null}

        {error ? <Alert kind="error">{error}</Alert> : null}

        <Button type="submit" size="lg" disabled={!file} loading={uploading}>
          {uploading ? "Uploading…" : "Upload document"}
        </Button>
      </form>

      {uploaded ? (
        <section
          aria-live="polite"
          className="rounded-xl border border-green-200 bg-green-50 p-6"
        >
          <div className="flex items-start gap-3">
            <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-success" aria-hidden="true" />
            <div className="flex min-w-0 flex-1 flex-col gap-1">
              <h2 className="font-semibold text-success">Document uploaded</h2>
              <dl className="mt-1 grid grid-cols-[6rem_1fr] gap-x-4 gap-y-1 text-sm">
                <dt className="text-success">File</dt>
                <dd className="truncate">{uploaded.filename}</dd>
                <dt className="text-success">Size</dt>
                <dd>{formatBytes(uploaded.file_size_bytes)}</dd>
                <dt className="text-success">Status</dt>
                <dd>{uploaded.status}</dd>
              </dl>
              <p className="mt-1 text-sm text-success">
                Processing begins shortly. Your document is stored privately and
                only accessible to your account.
              </p>
              <div className="mt-4 flex flex-wrap gap-3">
                {uploaded.id ? (
                  <Button href={`/documents/${uploaded.id}/processing`}>
                    View processing
                  </Button>
                ) : (
                  <Button href="/dashboard">Go to dashboard</Button>
                )}
                <Button variant="secondary" onClick={reset}>
                  Upload another
                </Button>
              </div>
              <p className="mt-2 text-sm text-success">
                <Link href="/dashboard" className="font-medium underline underline-offset-4">
                  Back to dashboard
                </Link>
              </p>
            </div>
          </div>
        </section>
      ) : null}
    </>
  );
}