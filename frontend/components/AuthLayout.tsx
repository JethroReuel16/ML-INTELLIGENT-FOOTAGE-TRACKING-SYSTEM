import { Crosshair, FileSearch, Layers, ScanSearch } from "lucide-react";
import type { ReactNode } from "react";

const POINTS = [
  {
    icon: Crosshair,
    title: "Find objects by image or description",
    text: "Upload a reference photo, describe the object, or combine both.",
  },
  {
    icon: Layers,
    title: "Search many sources at once",
    text: "Run one search across uploaded footage, CCTV streams and video files.",
  },
  {
    icon: FileSearch,
    title: "Review ranked evidence",
    text: "Jump straight to the moment each candidate appears in the footage.",
  },
];

/** Two-column frame shared by the sign-in and registration screens. */
export default function AuthLayout({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <main className="grid min-h-screen lg:grid-cols-[1.05fr_1fr]">
      <section className="relative hidden overflow-hidden border-r border-line bg-surface lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-60"
          style={{
            background:
              "linear-gradient(rgba(148,170,196,0.05) 1px, transparent 1px) 0 0 / 40px 40px, linear-gradient(90deg, rgba(148,170,196,0.05) 1px, transparent 1px) 0 0 / 40px 40px, radial-gradient(600px 400px at 30% 20%, rgba(69,188,205,0.12), transparent 70%)",
          }}
        />

        <div className="relative flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/12 text-accent ring-1 ring-accent/30">
            <ScanSearch size={20} aria-hidden />
          </span>
          <span className="text-[15px] font-semibold text-fg">ML Footage Tracking System</span>
        </div>

        <div className="relative max-w-md">
          <h2 className="text-3xl font-semibold leading-tight tracking-tight text-fg">
            Locate objects across hours of footage in minutes.
          </h2>
          <ul className="mt-10 space-y-6">
            {POINTS.map(({ icon: Icon, title: t, text }) => (
              <li key={t} className="flex gap-4">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-line-strong bg-surface-2 text-accent">
                  <Icon size={17} aria-hidden />
                </span>
                <div>
                  <p className="text-sm font-semibold text-fg">{t}</p>
                  <p className="mt-0.5 text-sm leading-relaxed text-muted">{text}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-faint">
          Access is restricted to authorised investigators.
        </p>
      </section>

      <section className="flex items-center justify-center px-4 py-12 sm:px-8">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/12 text-accent ring-1 ring-accent/30">
              <ScanSearch size={20} aria-hidden />
            </span>
            <span className="text-[15px] font-semibold text-fg">ML Footage Tracking System</span>
          </div>

          <h1 className="text-2xl font-semibold tracking-tight text-fg">{title}</h1>
          <p className="mt-1.5 text-sm text-muted">{subtitle}</p>

          <div className="mt-8">{children}</div>
        </div>
      </section>
    </main>
  );
}
