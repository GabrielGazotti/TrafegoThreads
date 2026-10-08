export const API_BASE = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000`;
export const WS_BASE =
  import.meta.env.VITE_WS_URL?.replace(/\/ws\/.*$/, "") || `ws://${window.location.hostname}:8000`;
