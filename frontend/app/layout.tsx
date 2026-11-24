import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import AppChrome from "@/components/AppChrome";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: {
    default: "ML Footage Tracking System",
    template: "%s · ML Footage Tracking System",
  },
  description:
    "Image- and text-guided object search and evidence review across CCTV and video footage.",
};

export const viewport: Viewport = {
  themeColor: "#0a0e13",
  colorScheme: "dark",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full">
        <AppChrome>{children}</AppChrome>
      </body>
    </html>
  );
}
