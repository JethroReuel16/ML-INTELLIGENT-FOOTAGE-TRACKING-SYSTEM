"use client";

import { LogIn } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useState } from "react";

import AuthLayout from "@/components/AuthLayout";
import { useAuth } from "@/components/AppChrome";
import PasswordInput from "@/components/PasswordInput";
import { Alert, Button, Field } from "@/components/ui";
import { getAuthConfig, getCurrentUser, loginUser } from "@/services/api";

/** Only allow same-site relative redirects. */
function safeNext(value: string | null): string {
  if (value && value.startsWith("/") && !value.startsWith("//")) return value;
  return "/dashboard";
}

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { setUser } = useAuth();
  const next = safeNext(params.get("next"));
  const justRegistered = params.get("registered") === "1";

  const [email, setEmail] = useState(params.get("email") ?? "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [registrationOpen, setRegistrationOpen] = useState(false);

  // Only advertise sign-up when the server allows it.
  useEffect(() => {
    let alive = true;
    getAuthConfig()
      .then((config) => alive && setRegistrationOpen(config.registration_enabled))
      .catch(() => {
        /* keep the link hidden */
      });
    return () => {
      alive = false;
    };
  }, []);

  // Already signed in? Skip the form.
  useEffect(() => {
    let alive = true;
    getCurrentUser()
      .then((u) => {
        if (!alive) return;
        setUser(u);
        router.replace(next);
      })
      .catch(() => {
        /* not signed in — show the form */
      });
    return () => {
      alive = false;
    };
  }, [router, next, setUser]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await loginUser(email.trim(), password);
      setUser(response.user);
      router.replace(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in. Please try again.");
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5" noValidate>
      {justRegistered && !error && (
        <Alert tone="success">Account created. Sign in to continue.</Alert>
      )}
      {error && <Alert tone="error">{error}</Alert>}

      <Field label="Email address" htmlFor="email">
        <input
          id="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@organisation.org"
          className="vt-input"
        />
      </Field>

      <Field label="Password" htmlFor="password">
        <PasswordInput
          id="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Your password"
        />
      </Field>

      <Button
        type="submit"
        size="lg"
        icon={LogIn}
        loading={loading}
        disabled={!email.trim() || !password}
        className="w-full"
      >
        {loading ? "Signing in…" : "Sign in"}
      </Button>

      <p className="text-center text-sm text-muted">
        Don&apos;t have an account?{" "}
        {registrationOpen ? (
          <Link href="/register" className="font-semibold text-accent hover:underline">
            Create one
          </Link>
        ) : (
          "Ask your administrator to create one."
        )}
      </p>
    </form>
  );
}

export default function LoginPage() {
  return (
    <AuthLayout title="Sign in" subtitle="Use your investigator account to continue.">
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </AuthLayout>
  );
}
