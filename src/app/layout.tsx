import type { Metadata } from "next";
import { Lexend, Outfit } from "next/font/google";
import "./globals.css";

// The variable names are the ones scripts/tokens.mjs writes into the font tokens.
const outfit = Outfit({ variable: "--font-outfit", subsets: ["latin"] });
const lexend = Lexend({ variable: "--font-lexend", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Arandu Reka · Orientação vocacional com inteligência artificial",
  description:
    "Um app de orientação vocacional com inteligência artificial, onde o aluno do ensino médio vive uma carreira antes de escolher.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" data-theme="dark" className={`${outfit.variable} ${lexend.variable}`}>
      <body>{children}</body>
    </html>
  );
}
