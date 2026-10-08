import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import App from "./App.jsx";
import ThreadsPage from "./pages/ThreadsPage.jsx";
import SchedulingPage from "./pages/SchedulingPage.jsx";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<App />}>
          <Route path="/threads" element={<ThreadsPage />} />
          <Route path="/scheduling" element={<SchedulingPage />} />
          <Route path="*" element={<Navigate to="/threads" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
