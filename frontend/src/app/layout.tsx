import type { Metadata } from "next";
// Fuentes empaquetadas con npm: el build no depende de descargar Google Fonts (fallaba en Vercel)
import "@fontsource-variable/fredoka";
import "@fontsource-variable/nunito";
import { AuthProvider } from "@/lib/auth";
import "./globals.css";

export const metadata: Metadata = {
  title: "Aprende Multiagente",
  description: "Sistema multiagente que personaliza contenido pedagógico para primaria.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="min-h-screen bg-slate-50 font-body text-slate-800 antialiased">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
