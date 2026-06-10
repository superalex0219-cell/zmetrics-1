import React from "react";
import ReactDOM from "react-dom/client";

import { initKeycloak } from "./api";
import App from "./App";
import "./styles.css";

const kc = initKeycloak();

let rendered = false;
function renderApp() {
  if (rendered) return;
  rendered = true;
  ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
}

const keycloakFallbackTimer = window.setTimeout(() => {
  console.warn("Keycloak init timed out; rendering unauthenticated shell.");
  renderApp();
}, 3000);

kc.init({
  onLoad: "login-required",
  pkceMethod: "S256",
}).catch((err) => {
  console.warn("Keycloak init failed; rendering unauthenticated shell.", err);
}).finally(() => {
  window.clearTimeout(keycloakFallbackTimer);
  renderApp();
});
