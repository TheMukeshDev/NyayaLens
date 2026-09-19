import { UploadForm } from "./upload-form";

export const metadata = { title: "Upload Document" };

export default function UploadPage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight text-navy">Upload document</h1>
        <p className="max-w-2xl text-base text-muted">
          Add a legal document to begin your review. Files are stored privately
          and only accessible to your account.
        </p>
      </div>

      <UploadForm />

      <section className="rounded-xl border border-line bg-surface p-6">
        <h2 className="text-lg font-semibold tracking-tight text-navy">What happens next</h2>
        <ol className="mt-3 flex flex-col gap-2 text-sm text-muted">
          <li>1. Your file is uploaded securely and scanned.</li>
          <li>2. Text is extracted and checked against supported formats.</li>
          <li>3. NyayaLens reviews clauses and prepares your summary.</li>
          <li>4. You get a plain-language overview with verifiable sources.</li>
        </ol>
      </section>
    </div>
  );
}