import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Configurazione di Vite (lo strumento che avvia e compila il frontend).
export default defineConfig({
  plugins: [react()],
});
