import type { Config } from "tailwindcss";

const config: Config = {
    darkMode: "class",
    content: [
        "./pages/**/*.{js,ts,jsx,tsx,mdx}",
        "./components/**/*.{js,ts,jsx,tsx,mdx}",
        "./app/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: "#e11d48",
                "accent-red": "#9f1239",
                "bg-dark": "#050506",
                "panel": "#0d0d10",
                "panel-light": "#15151a",
            },
            fontFamily: {
                display: ["Space Grotesk", "sans-serif"],
            },
        },
    },
    plugins: [],
};
export default config;
