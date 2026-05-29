import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { WindowPreset } from "./types";

interface AppState {
  window: WindowPreset;
  setWindow: (w: WindowPreset) => void;

  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      window: "24h",
      setWindow: (window) => set({ window }),

      sidebarCollapsed: false,
      toggleSidebar: () =>
        set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
    }),
    {
      name: "orchestrix-gateway-app",
      partialize: (state) => ({
        window: state.window,
        sidebarCollapsed: state.sidebarCollapsed,
      }),
    },
  ),
);
