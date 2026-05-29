"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Toolbar } from "@/components/macos/toolbar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api-client";
import { formatRelativeTime } from "@/lib/format";
import { useCurrentUser } from "@/lib/use-auth";

export default function SettingsPage() {
  return (
    <>
      <Toolbar
        title="Settings"
        subtitle="Manage your account and gateway access"
        showWindowPicker={false}
      />
      <div className="p-6 grid gap-6 max-w-4xl">
        <AccountCard />
        <ApiKeysCard />
      </div>
    </>
  );
}

function AccountCard() {
  const { data: user, isPending } = useCurrentUser();
  return (
    <Card>
      <CardHeader>
        <CardTitle>Account</CardTitle>
        <CardDescription>
          The user this dashboard is signed in as.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isPending || !user ? (
          <Skeleton className="h-8 w-64" />
        ) : (
          <dl className="grid sm:grid-cols-2 gap-4 text-sm">
            <Field label="Name" value={user.name ?? "—"} />
            <Field label="Email" value={user.email} mono />
            <Field
              label="Member since"
              value={formatRelativeTime(user.created_at)}
            />
            <Field label="User ID" value={user.id} mono />
          </dl>
        )}
      </CardContent>
    </Card>
  );
}

function Field({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </dt>
      <dd className={mono ? "font-mono text-sm" : "text-sm font-medium"}>
        {value}
      </dd>
    </div>
  );
}

function ApiKeysCard() {
  const qc = useQueryClient();
  const { data, isPending, error } = useQuery({
    queryKey: ["api-keys"],
    queryFn: () => api.apiKeys.list(),
  });

  const [open, setOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [created, setCreated] = useState<{ name: string; key: string } | null>(
    null,
  );

  const createMutation = useMutation({
    mutationFn: (name: string) => api.apiKeys.create(name),
    onSuccess: (resp) => {
      setCreated({ name: resp.name, key: resp.key });
      setNewName("");
      qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const revokeMutation = useMutation({
    mutationFn: (id: string) => api.apiKeys.revoke(id),
    onSuccess: () => {
      toast.success("API key revoked");
      qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div className="space-y-1">
          <CardTitle>API keys</CardTitle>
          <CardDescription>
            Keys that authenticate calls to{" "}
            <code className="text-xs rounded bg-muted px-1 py-0.5">
              /v1/chat/completions
            </code>
            . Keep these out of source control.
          </CardDescription>
        </div>
        <Button onClick={() => setOpen(true)}>
          <Plus className="h-4 w-4" />
          New key
        </Button>
      </CardHeader>
      <CardContent>
        {isPending ? (
          <div className="space-y-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : error ? (
          <p className="text-sm text-destructive">
            {(error as Error).message}
          </p>
        ) : data?.length === 0 ? (
          <p className="text-sm text-muted-foreground">No API keys yet.</p>
        ) : (
          <ul className="divide-y divide-border/60 rounded-xl border border-border/60 overflow-hidden">
            {data?.map((row) => (
              <li
                key={row.id}
                className="flex items-center justify-between gap-3 px-4 py-3"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium truncate">{row.name}</span>
                    {row.is_active ? (
                      <Badge variant="success">Active</Badge>
                    ) : (
                      <Badge variant="destructive">Revoked</Badge>
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground flex flex-wrap items-center gap-3 mt-0.5">
                    <span className="font-mono">{row.key_preview}</span>
                    <span>created {formatRelativeTime(row.created_at)}</span>
                    {row.last_used_at && (
                      <span>
                        last used {formatRelativeTime(row.last_used_at)}
                      </span>
                    )}
                  </div>
                </div>
                {row.is_active && (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => revokeMutation.mutate(row.id)}
                    title="Revoke"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </CardContent>

      <Dialog
        open={open}
        onOpenChange={(o) => {
          setOpen(o);
          if (!o) setCreated(null);
        }}
      >
        <DialogContent>
          {!created ? (
            <>
              <DialogHeader>
                <DialogTitle>Create API key</DialogTitle>
                <DialogDescription>
                  Give the key a name so you can identify it later.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-2">
                <Label htmlFor="key-name">Name</Label>
                <Input
                  id="key-name"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. local dev"
                />
              </div>
              <DialogFooter>
                <Button
                  variant="ghost"
                  onClick={() => setOpen(false)}
                  disabled={createMutation.isPending}
                >
                  Cancel
                </Button>
                <Button
                  onClick={() => createMutation.mutate(newName.trim())}
                  disabled={!newName.trim() || createMutation.isPending}
                >
                  Create
                </Button>
              </DialogFooter>
            </>
          ) : (
            <>
              <DialogHeader>
                <DialogTitle>API key created</DialogTitle>
                <DialogDescription>
                  Save this key now. You won&apos;t see it again.
                </DialogDescription>
              </DialogHeader>
              <div className="rounded-lg bg-muted/50 border border-border/60 p-3 font-mono text-xs break-all">
                {created.key}
              </div>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => {
                    navigator.clipboard.writeText(created.key);
                    toast.success("Copied to clipboard");
                  }}
                >
                  <Copy className="h-4 w-4" /> Copy
                </Button>
                <Button onClick={() => setOpen(false)}>Done</Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </Card>
  );
}
