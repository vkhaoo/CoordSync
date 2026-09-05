import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Configurazione di Vite (lo strumento che avvia e compila il frontend) e dei
// test dell'interfaccia.
export default defineConfig({
  plugins: [react()],
  test: {
    // jsdom: un finto browser dentro Node. Serve perche' api.js usa
    // localStorage e fetch, che in Node puro non esistono.
    environment: "jsdom",
    include: ["src/**/*.test.js"],
  },
});
