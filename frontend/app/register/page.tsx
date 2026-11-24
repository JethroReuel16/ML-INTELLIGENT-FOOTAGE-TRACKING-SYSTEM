"use client";

import { UserPlus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import AuthLayout from "@/components/AuthLayout";
import PasswordInput from "@/components/PasswordInput";
import { Alert, Button, ButtonLink, Field } from "@/components/ui";
import { getAuthConfig, registerUser } from "@/services/api";

const MIN_PASSWORD = 8;

export default function RegisterPage() {
  const router = useRouter();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [touched, setTouched] = useState(false);
  const [registrationOpen, setRegistrationOpen] = useState<boolean | null>(null);

  useEffect(() => {
    let alive = true;
    getAuthConfig()
      .then((config) => alive && setRegistrationOpen(config.registration_enabled))
      .catch(() => alive && setRegistrationOpen(true)); // let the server decide on submit
    return () => {
      alive = false;
    };
  }, []);

  const passwordError =
    touched && password.length > 0 && password.length < MIN_PASSWORD
      ? `Use at least ${MIN_PASSWORD} characters.`
      : "";
  const confirmError =
    touched && confirm.length > 0 && confirm !== password ? "Passwords do not match." : "";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTouched(true);
    setError("");

    if (!fullName.trim()) return setError("Enter your full name.");
    if (password.length < MIN_PASSWORD)
      return setError(`Password must contain at least ${MIN_PASSWORD} characters.`);
    if (password !== confirm) return setError("Passwords do not match.");

    setLoading(true);

    try {
      await registerUser({ full_name: fullName.trim(), email: email.trim(), password });
      router.replace(`/login?registered=1&email=${encodeURIComponent(email.trim())}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed. Please try again.");
      setLoading(false);
    }
  }

  if (registrationOpen === false) {
    return (
      <AuthLayout title="Accounts are managed by your administrator" subtitle="Self-registration is turned off on this server.">
        <Alert tone="info">
          Ask an administrator to create an account for you. They can do this with the server&apos;s
          management command.
        </Alert>
        <ButtonLink href="/login" variant="secondary" className="mt-6 w-full">
          Back to sign in
        </ButtonLink>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title="Create an account" subtitle="Register to start searching footage.">
      <form onSubmit={handleSubmit} className="space-y-5" noValidate>
        {error && <Alert tone="error">{error}</Alert>}

        <Field label="Full name" htmlFor="full-name">
          <input
            id="full-name"
            autoComplete="name"
            required
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Jane Banda"
            className="vt-input"
          />
        </Field>

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

        <Field
          label="Password"
          htmlFor="password"
          hint={`At least ${MIN_PASSWORD} characters.`}
          error={passwordError}
        >
          <PasswordInput
            id="password"
            autoComplete="new-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onBlur={() => setTouched(true)}
            aria-invalid={!!passwordError}
          />
        </Field>

        <Field label="Confirm password" htmlFor="confirm" error={confirmError}>
          <PasswordInput
            id="confirm"
            autoComplete="new-password"
            required
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            onBlur={() => setTouched(true)}
            aria-invalid={!!confirmError}
          />
        </Field>

        <Button
          type="submit"
          size="lg"
          icon={UserPlus}
          loading={loading}
          disabled={!fullName.trim() || !email.trim() || !password || !confirm}
          className="w-full"
        >
          {loading ? "Creating account…" : "Create account"}
        </Button>

        <p className="text-center text-sm text-muted">
          Already registered?{" "}
          <Link href="/login" className="font-semibold text-accent hover:underline">
            Sign in
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
}
