import React from "react";
import ReactDOM from "react-dom/client";
import { Toaster } from "sonner";
import App from "./App";
import "./styles/globals.css";
import { initializeTheme, useTheme } from "./theme/theme";

// Theme init — session is already loaded from localStorage by the Zustand store
initializeTheme();

function Root() {
  const { theme } = useTheme();

  return (
    <React.StrictMode>
      <App />
      <Toaster
        position="top-right"
        theme={theme}
        richColors
        toastOptions={{
          className: "border border-white/10 bg-slate-950 text-slate-100",
        }}
      />
    </React.StrictMode>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <Root />
);
