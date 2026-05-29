"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { AuthShell } from "@/components/auth/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSignup } from "@/lib/use-auth";

export default function SignupPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const signup = useSignup();

  const passwordOk = useMemo(() => password.length >= 8, [password]);

  return (
    <AuthShell
      title="Create your account"
      subtitle="One email, one password — we'll provision your gateway and an API key."
      footer={
        <>
          Already have an account?{" "}
          <Link href="/login" className="text-primary font-medium hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (!passwordOk) return;
          signup.mutate({
            email,
            password,
            name: name.trim() || undefined,
          });
        }}
      >
        <div className="space-y-1.5">
          <Label htmlFor="name">Name (optional)</Label>
          <Input
            id="name"
            type="text"
            autoComplete="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ada Lovelace"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 8 characters"
          />
          <p
            className={`text-xs ${passwordOk || password.length === 0 ? "text-muted-foreground" : "text-destructive"}`}
          >
            Use at least 8 characters. A passphrase is fine.
          </p>
        </div>
        {signup.error && (
          <p className="text-sm text-destructive">
            {(signup.error as Error).message}
          </p>
        )}
        <Button
          type="submit"
          className="w-full"
          disabled={signup.isPending || !passwordOk}
        >
          {signup.isPending ? "Creating account…" : "Create account"}
        </Button>
        <p className="text-[11px] text-muted-foreground text-center">
          By signing up you accept that this is a portfolio demo with no SLA.
        </p>
      </form>
    </AuthShell>
  );
}
