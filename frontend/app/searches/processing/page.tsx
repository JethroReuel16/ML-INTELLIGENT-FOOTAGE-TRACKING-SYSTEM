"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ProcessingPage() {
  const router = useRouter();

  useEffect(() => {
    /*
     * The current backend performs the search synchronously.
     * This page is therefore mainly a visual processing state.
     *
     * The New Search page currently redirects directly to the
     * completed result once the backend responds.
     */

    const timer = setTimeout(() => {
      router.push("/searches/new");
    }, 30000);

    return () => clearTimeout(timer);
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-6">
      <div className="w-full max-w-xl rounded-2xl border bg-white p-10 text-center shadow-sm">
        <div className="mx-auto mb-6 h-14 w-14 animate-spin rounded-full border-4 border-gray-200 border-t-black" />

        <h1 className="text-2xl font-bold text-gray-900">
          VisionTrace AI is searching
        </h1>

        <p className="mx-auto mt-3 max-w-md text-gray-600">
          The system is analyzing the video, detecting
          objects, tracking candidates and comparing their
          visual features with your reference image.
        </p>

        <div className="mt-8 space-y-3 text-left">
          <div className="rounded-lg bg-gray-50 p-3 text-sm">
            ✓ Reference image received
          </div>

          <div className="rounded-lg bg-gray-50 p-3 text-sm">
            ✓ Video footage received
          </div>

          <div className="rounded-lg bg-gray-50 p-3 text-sm">
            • Detecting and tracking objects
          </div>

          <div className="rounded-lg bg-gray-50 p-3 text-sm">
            • Comparing visual features
          </div>
        </div>

        <p className="mt-8 text-xs text-gray-400">
          Please keep this page open while processing.
        </p>
      </div>
    </main>
  );
}