"use client";

import {
  History,
  LayoutDashboard,
  LogOut,
  Menu,
  Plus,
  ScanSearch,
  Search,
  Video,
  WifiOff,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import {
  AuthUser,
  getCurrentUser,
  isUnauthorized,
  logoutUser,
} from "@/services/api";
import { Button, ButtonLink, Card, EmptyState, Spinner, cn } from "./ui";

export const APP_NAME = "ML Footage Tracking System";

/* ------------------------------------------------------------------ */
/* Auth context                                                        */
/* ------------------------------------------------------------------ */

interface AuthContextValue {
  user: AuthUser | null;
  setUser: (user: AuthUser | null) => void;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AppChrome>.");
  return ctx;
}

/* ------------------------------------------------------------------ */
/* Navigation                                                          */
/* ------------------------------------------------------------------ */

const NAV = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/searches/new", label: "New search", icon: Search },
  { href: "/history", label: "Case history", icon: History },
  { href: "/sources", label: "Video sources", icon: Video },
];

/** Routes rendered without the console shell and without a session check. */
const PUBLIC_ROUTES = ["/login", "/register"];

function isActive(pathname: string, href: string): boolean {
  if (href === "/history") {
    // Result and evidence pages belong to a case in history.
    return (
      pathname.startsWith("/history") ||
      pathname.startsWith("/searches/results") ||
      pathname.startsWith("/searches/evidence") ||
      pathname.startsWith("/searches/multi-results")
    );
  }
  return pathname === href || pathname.startsWith(href + "/");
}

function initials(name?: string): string {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "?";
}

type SessionStatus = "checking" | "ready" | "offline";

/* ------------------------------------------------------------------ */
/* Shell                                                               */
/* ------------------------------------------------------------------ */

export default function AppChrome({ children }: { children: ReactNode }) {
  const pathname = usePathname() || "/";
  const router = useRouter();
  const isPublic = PUBLIC_ROUTES.includes(pathname);

  const [user, setUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<SessionStatus>("checking");
  const [attempt, setAttempt] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);

  // Verify the session once when entering the protected area.
  useEffect(() => {
    if (isPublic) return;

    let alive = true;

    getCurrentUser()
      .then((u) => {
        if (!alive) return;
        setUser(u);
        setStatus("ready");
      })
      .catch((err) => {
        if (!alive) return;
        if (isUnauthorized(err)) {
          setUser(null);
          const next = window.location.pathname + window.location.search;
          router.replace(`/login?next=${encodeURIComponent(next)}`);
        } else {
          setStatus("offline");
        }
      });

    return () => {
      alive = false;
    };
    // Re-run when moving between public/protected areas or on retry.
  }, [isPublic, attempt, router]);

  const signOut = useCallback(async () => {
    setSigningOut(true);
    try {
      await logoutUser();
    } catch {
      /* the session is discarded client-side regardless */
    } finally {
      setUser(null);
      setStatus("checking");
      setSigningOut(false);
      router.replace("/login");
    }
  }, [router]);

  const updateUser = useCallback((u: AuthUser | null) => {
    setUser(u);
    setStatus(u ? "ready" : "checking");
  }, []);

  const ctx: AuthContextValue = { user, setUser: updateUser, signOut };

  if (isPublic) {
    return <AuthContext.Provider value={ctx}>{children}</AuthContext.Provider>;
  }

  return (
    <AuthContext.Provider value={ctx}>
      {/* ================= SIDEBAR ================= */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-(--sidebar-w) flex-col border-r border-line bg-surface transition-transform duration-200",
          menuOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        )}
        aria-label="Main navigation"
      >
        <div className="flex items-center gap-3 border-b border-line px-5 py-4">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent/12 text-accent ring-1 ring-accent/30">
            <ScanSearch size={19} aria-hidden />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold leading-tight text-fg">ML Footage Tracking</p>
            <p className="vt-eyebrow mt-0.5">System</p>
          </div>
          <button
            type="button"
            className="rounded-md p-1.5 text-muted hover:bg-surface-2 hover:text-fg md:hidden"
            onClick={() => setMenuOpen(false)}
            aria-label="Close menu"
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-3 pt-4">
          <ButtonLink
            href="/searches/new"
            icon={Plus}
            className="w-full"
            onClick={() => setMenuOpen(false)}
          >
            New search
          </ButtonLink>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4">
          <ul className="space-y-0.5">
            {NAV.map(({ href, label, icon: Icon }) => {
              const active = isActive(pathname, href);
              return (
                <li key={href}>
                  <Link
                    href={href}
                    onClick={() => setMenuOpen(false)}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors",
                      active
                        ? "bg-accent/10 font-medium text-fg ring-1 ring-accent/25"
                        : "text-muted hover:bg-surface-2 hover:text-fg"
                    )}
                  >
                    <Icon size={17} className={active ? "text-accent" : undefined} aria-hidden />
                    {label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="border-t border-line p-3">
          <div className="flex items-center gap-3 rounded-lg px-2 py-2">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-3 text-xs font-semibold text-fg-2 ring-1 ring-line-strong">
              {initials(user?.full_name)}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[13px] font-medium text-fg">
                {user?.full_name || "Signed in"}
              </p>
              <p className="truncate text-xs text-faint">{user?.email || " "}</p>
            </div>
            <button
              type="button"
              onClick={() => void signOut()}
              disabled={signingOut}
              title="Sign out"
              aria-label="Sign out"
              className="rounded-md p-2 text-muted transition-colors hover:bg-danger/10 hover:text-danger disabled:opacity-50"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      {menuOpen && (
        <button
          type="button"
          aria-label="Close menu"
          className="fixed inset-0 z-30 bg-black/60 md:hidden"
          onClick={() => setMenuOpen(false)}
        />
      )}

      {/* ================= CONTENT ================= */}
      <div className="flex min-h-screen flex-col md:pl-(--sidebar-w)">
        {/* Mobile top bar */}
        <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-line bg-bg/85 px-4 py-3 backdrop-blur md:hidden">
          <button
            type="button"
            className="rounded-md border border-line p-2 text-fg-2"
            onClick={() => setMenuOpen(true)}
            aria-label="Open menu"
          >
            <Menu size={18} />
          </button>
          <span className="flex items-center gap-2 text-sm font-semibold text-fg">
            <ScanSearch size={17} className="text-accent" aria-hidden />
            ML Footage Tracking
          </span>
        </header>

        <div className="flex-1">
          {status === "ready" ? (
            children
          ) : status === "offline" ? (
            <div className="px-4 py-16">
              <Card className="mx-auto max-w-md">
                <EmptyState
                  icon={WifiOff}
                  title="Server unavailable"
                  description="The ML Footage Tracking server could not be reached. Check that the backend is running, then try again."
                  action={
                    <Button
                      variant="secondary"
                      onClick={() => {
                        setStatus("checking");
                        setAttempt((n) => n + 1);
                      }}
                    >
                      Try again
                    </Button>
                  }
                />
              </Card>
            </div>
          ) : (
            <div className="flex items-center justify-center gap-3 py-32 text-sm text-muted" role="status">
              <Spinner /> Verifying session…
            </div>
          )}
        </div>
      </div>
    </AuthContext.Provider>
  );
}
