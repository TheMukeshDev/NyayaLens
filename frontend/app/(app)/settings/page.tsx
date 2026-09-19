import { ShieldCheck, UserRound } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { serverApi } from "@/lib/api/server";
import type { UserOut } from "@/lib/types";

export const metadata = { title: "Settings" };

export default async function SettingsPage() {
  const result = await serverApi<UserOut>("/auth/me");
  const user = result.ok && result.data ? result.data : null;

  return (
    <div className="flex max-w-3xl flex-col gap-5">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight text-navy">Settings</h1>
        <p className="max-w-2xl text-base text-muted">
          Manage your account and review preferences.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle as="h2" className="flex items-center gap-2">
            <UserRound className="size-4.5 text-brand" aria-hidden="true" />
            Account
          </CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-sm font-medium text-muted">Email</dt>
              <dd className="mt-0.5 text-sm text-ink">{user?.email ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted">Account role</dt>
              <dd className="mt-0.5 text-sm text-ink">{user?.role ?? "Member"}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted">User ID</dt>
              <dd className="mt-0.5 text-sm text-ink">{user?.id ?? "—"}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle as="h2" className="flex items-center gap-2">
            <ShieldCheck className="size-4.5 text-brand" aria-hidden="true" />
            Security
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted">
            Account security is managed by your identity provider. To change
            your password, sign out and use the password reset option on the
            login page.
          </p>
        </CardContent>
      </Card>

      <p className="text-sm text-muted">
        Need to delete a document or your account? Reach out to support and we
        will guide you through it.
      </p>
    </div>
  );
}