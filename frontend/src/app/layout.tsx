import type { Metadata } from "next";
import { Fredoka, Nunito } from "next/font/google";
import { AuthProvider } from "@/lib/auth";
import "./globals.css";

const display = Fredoka({ subsets: ["latin"], variable: "--font-display", weight: ["500", "600", "700"] });
const body = Nunito({ subsets: ["latin"], variable: "--font-body" });

export const metadata: Metadata = {
  title: "Aprende Multiagente",
  description: "Sistema multiagente que personaliza contenido pedagógico para primaria.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className={`${display.variable} ${body.variable} min-h-screen bg-slate-50 font-body text-slate-800 antialiased`}>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
