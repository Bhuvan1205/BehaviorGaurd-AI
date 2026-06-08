/**
 * useLiveStore.js
 *
 * Global Zustand store for the SSE live event stream.
 * The connection is opened ONCE in AppLayout and persists across all page
 * navigations.  Any component can read events from this store without
 * owning the connection or losing data when it unmounts.
 */

import { create } from "zustand";
import { openLiveStream } from "../services/api";

const MAX_EVENTS = 120;
const BURST_THRESHOLD = 3;
const BURST_WINDOW_MS = 60_000;

export const useLiveStore = create((set, get) => ({
  // ── Connection state ──────────────────────────────────────────────────────
  connected: false,
  connectionError: "",
  streamRef: null,          // { close() } handle

  // ── Events ────────────────────────────────────────────────────────────────
  events: [],               // all received scored events (newest first)
  eventsCount: 0,           // total since store was created

  // ── Scoreboard ────────────────────────────────────────────────────────────
  scoreboard: {},           // { [user_id]: { ...peak risk record } }

  // ── Burst detection ───────────────────────────────────────────────────────
  burstAlert: false,
  _recentHighRisk: [],      // timestamps of recent anomalies
  _burstTimer: null,

  // ── Open / close SSE connection ───────────────────────────────────────────
  openStream() {
    const existing = get().streamRef;
    if (existing) return; // already open

    const handle = openLiveStream(
      // onEvent
      (evt) => {
        if (evt.type === "connected") {
          set({ connected: true, connectionError: "" });
          return;
        }

        // Ignore non-event frames
        if (!evt.user_id) return;

        set((state) => {
          const newEvents = [evt, ...state.events].slice(0, MAX_EVENTS);
          const newCount  = state.eventsCount + 1;

          // ── Scoreboard update ──────────────────────────────────────────
          const existing = state.scoreboard[evt.user_id];
          const newScoreboard = { ...state.scoreboard };
          if (!existing || evt.risk_score > existing.risk_score) {
            newScoreboard[evt.user_id] = {
              user_id:     evt.user_id,
              full_name:   evt.full_name,
              employee_id: evt.employee_id,
              department:  evt.department,
              risk_score:  evt.risk_score,
              risk_level:  evt.risk_level,
              anomaly_flag: evt.anomaly_flag,
              last_seen:   evt.timestamp,
            };
          }

          // ── Burst detection ────────────────────────────────────────────
          let burstAlert = state.burstAlert;
          let recentHighRisk = state._recentHighRisk;
          let burstTimer = state._burstTimer;

          if (evt.anomaly_flag) {
            const now = Date.now();
            recentHighRisk = recentHighRisk
              .filter((t) => now - t < BURST_WINDOW_MS)
              .concat(now);

            if (recentHighRisk.length >= BURST_THRESHOLD && !burstAlert) {
              burstAlert = true;
              if (burstTimer) clearTimeout(burstTimer);
              burstTimer = setTimeout(
                () => set({ burstAlert: false, _burstTimer: null }),
                10_000,
              );
            }
          }

          return {
            events:          newEvents,
            eventsCount:     newCount,
            connected:       true,
            scoreboard:      newScoreboard,
            burstAlert,
            _recentHighRisk: recentHighRisk,
            _burstTimer:     burstTimer,
          };
        });
      },
      // onError — auto-reconnect
      () => {
        set({ connected: false, connectionError: "Stream disconnected. Reconnecting..." });
        // Close old ref so openStream() can create a fresh one
        set({ streamRef: null });
        setTimeout(() => get().openStream(), 3000);
      },
    );

    set({ streamRef: handle });
  },

  closeStream() {
    const handle = get().streamRef;
    if (handle) handle.close();
    const timer = get()._burstTimer;
    if (timer) clearTimeout(timer);
    set({ streamRef: null, connected: false, _burstTimer: null });
  },

  // ── Derived helpers ───────────────────────────────────────────────────────
  getAnomalies() {
    return get().events.filter((e) => e.anomaly_flag);
  },

  getSortedScoreboard() {
    return Object.values(get().scoreboard)
      .sort((a, b) => b.risk_score - a.risk_score)
      .slice(0, 10);
  },
}));
