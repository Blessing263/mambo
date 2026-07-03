import type { Metadata } from "next";
import { Inter, Spectral, Hanken_Grotesk } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const spectral = Spectral({ subsets: ["latin"], weight: ["500", "600", "700"], variable: "--font-spectral", display: "swap" });
const hanken = Hanken_Grotesk({ subsets: ["latin"], variable: "--font-hanken", display: "swap" });

export const metadata: Metadata = {
  title: "Mambo — Government of Zimbabwe",
  description:
    "Ask the Government of Zimbabwe anything. Plain-language answers drawn only from official ministry documents, with the source always shown.",
  icons: { icon: "/favicon.svg" },
};

// Set the theme before first paint to avoid a flash. Honours a saved choice, else
// the OS preference. Runs inline in <head> before hydration.
const themeScript = `(function(){try{var t=localStorage.getItem('mambo-theme');if(t!=='light'&&t!=='dark'){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}document.documentElement.setAttribute('data-theme',t);}catch(e){document.documentElement.setAttribute('data-theme','light');}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${spectral.variable} ${hanken.variable}`}
    >
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        {/* Material Symbols: loaded via <link> (not CSS @import) — browsers ignore
            @import after other rules, e.g. next/font's @font-face. */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap"
        />
      </head>
      <body className="min-h-screen antialiased" style={{ background: "var(--bg-primary)", color: "var(--text-primary)" }}>
        {children}
      </body>
    </html>
  );
}
