"use client";

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { api } from "@/lib/api";

interface ClockState {
  demoNow: string;
  minDate: string;
  maxDate: string;
  loading: boolean;
  setClock: (ts: string) => Promise<void>;
  refresh: () => Promise<void>;
}

const ClockContext = createContext<ClockState>({
  demoNow: "",
  minDate: "",
  maxDate: "",
  loading: true,
  setClock: async () => {},
  refresh: async () => {},
});

export function ClockProvider({ children }: { children: ReactNode }) {
  const [demoNow, setDemoNow] = useState("");
  const [minDate, setMinDate] = useState("");
  const [maxDate, setMaxDate] = useState("");
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await api.getClock();
      setDemoNow(data.demo_now);
      setMinDate(data.min);
      setMaxDate(data.max);
    } catch {
      setDemoNow("2021-11-24T07:00:00");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const setClock = useCallback(async (ts: string) => {
    try {
      const data = await api.setClock(ts);
      setDemoNow(data.demo_now);
    } catch (e) {
      throw e;
    }
  }, []);

  return (
    <ClockContext.Provider value={{ demoNow, minDate, maxDate, loading, setClock, refresh }}>
      {children}
    </ClockContext.Provider>
  );
}

export function useClock() {
  return useContext(ClockContext);
}
