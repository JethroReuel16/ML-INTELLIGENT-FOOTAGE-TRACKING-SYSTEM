"use client";

import { ChangeEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { startSearch } from "../../../services/api";

export default function NewSearchPage() {
  const router = useRouter();

  const [referenceImage, setReferenceImage] =
    useState<File | null>(null);

  const [video, setVideo] = useState<File | null>(null);

  const [isSearching, setIsSearching] = useState(false);

  const [error, setError] = useState("");

  const handleReferenceChange = (
    event: ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    if (!file.type.startsWith("image/")) {
      setError("Please select a valid image file.");
      return;
    }

    setReferenceImage(file);
    setError("");
  };

  const handleVideoChange = (
    event: ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    if (!file.type.startsWith("video/")) {
      setError("Please select a valid video file.");
      return;
    }

    setVideo(file);
    setError("");
  };

  const handleStartSearch = async () => {
    if (!referenceImage) {
      setError("Please upload a reference image.");
      return;
    }

    if (!video) {
      setError("Please upload a video.");
      return;
    }

    try {
      setIsSearching(true);
      setError("");

      /*
       * Store the files temporarily in sessionStorage is not possible
       * because File objects cannot be serialized.
       *
       * The actual search is started here and the backend processes
       * the uploaded files.
       */

      const response = await startSearch(
        referenceImage,
        video
      );

      if (!response.result?.search_id) {
        throw new Error(
          "Search completed but no search ID was returned."
        );
      }

      router.push(
        `/searches/results/${response.result.search_id}`
      );
    } catch (err) {
      console.error(err);

      const message =
        err instanceof Error
          ? err.message
          : "Unable to complete the search.";

      setError(message);
      setIsSearching(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-5xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            New Object Search
          </h1>

          <p className="mt-2 text-gray-600">
            Upload a reference image and video footage
            to find matching objects.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          {/* Reference Image */}
          <section className="rounded-2xl border bg-white p-6 shadow-sm">
            <div className="mb-5">
              <h2 className="text-lg font-semibold text-gray-900">
                Reference Image
              </h2>

              <p className="mt-1 text-sm text-gray-500">
                Upload the object you want VisionTrace AI
                to search for.
              </p>
            </div>

            <label className="flex min-h-60 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 bg-gray-50 p-6 text-center transition hover:border-gray-500">
              <input
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleReferenceChange}
              />

              {referenceImage ? (
                <>
                  <div className="mb-3 text-4xl">
                    ✓
                  </div>

                  <p className="font-medium text-gray-900">
                    {referenceImage.name}
                  </p>

                  <p className="mt-1 text-sm text-gray-500">
                    {(referenceImage.size / 1024 / 1024).toFixed(
                      2
                    )}{" "}
                    MB
                  </p>
                </>
              ) : (
                <>
                  <div className="mb-3 text-4xl">
                    +
                  </div>

                  <p className="font-medium text-gray-900">
                    Upload reference image
                  </p>

                  <p className="mt-1 text-sm text-gray-500">
                    JPG, PNG, WEBP
                  </p>
                </>
              )}
            </label>
          </section>

          {/* Video */}
          <section className="rounded-2xl border bg-white p-6 shadow-sm">
            <div className="mb-5">
              <h2 className="text-lg font-semibold text-gray-900">
                Video Footage
              </h2>

              <p className="mt-1 text-sm text-gray-500">
                Upload CCTV or other video footage to
                search.
              </p>
            </div>

            <label className="flex min-h-60 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 bg-gray-50 p-6 text-center transition hover:border-gray-500">
              <input
                type="file"
                accept="video/*"
                className="hidden"
                onChange={handleVideoChange}
              />

              {video ? (
                <>
                  <div className="mb-3 text-4xl">
                    ✓
                  </div>

                  <p className="font-medium text-gray-900">
                    {video.name}
                  </p>

                  <p className="mt-1 text-sm text-gray-500">
                    {(video.size / 1024 / 1024).toFixed(
                      2
                    )}{" "}
                    MB
                  </p>
                </>
              ) : (
                <>
                  <div className="mb-3 text-4xl">
                    +
                  </div>

                  <p className="font-medium text-gray-900">
                    Upload video footage
                  </p>

                  <p className="mt-1 text-sm text-gray-500">
                    MP4, AVI, MOV
                  </p>
                </>
              )}
            </label>
          </section>
        </div>

        {/* Error */}
        {error && (
          <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Search Button */}
        <div className="mt-8 flex justify-end">
          <button
            type="button"
            onClick={handleStartSearch}
            disabled={isSearching}
            className="rounded-xl bg-black px-8 py-3 font-semibold text-white transition hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSearching
              ? "Searching..."
              : "Start Object Search"}
          </button>
        </div>
      </div>
    </main>
  );
}