import { useEffect, useState } from "react";

export function useAutoRefresh(intervalSec: number | null): number {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!intervalSec) return;
    const id = setInterval(() => setTick((t) => t + 1), intervalSec * 1000);
    return () => clearInterval(id);
  }, [intervalSec]);
  return tick;
}
