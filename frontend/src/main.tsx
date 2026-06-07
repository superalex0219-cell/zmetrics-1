import React from "react";
import ReactDOM from "react-dom/client";

import { initKeycloak } from "./api";
import App from "./App";
import "./styles.css";

const kc = initKeycloak();

kc.init({
  onLoad: "login-required",
  pkceMethod: "S256",
}).then(() => {
  ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
});
