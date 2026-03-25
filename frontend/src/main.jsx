import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
import { BrowserRouter } from "react-router-dom";
import { RealTimeProvider } from "./context/RealTimeContext";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <RealTimeProvider>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </RealTimeProvider>
  </React.StrictMode>
);