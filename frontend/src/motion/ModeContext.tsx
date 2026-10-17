import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import type { ModeKey } from './modeConfig';

type ModeContextValue = { mode: ModeKey; setMode: (mode: ModeKey) => void };

const ModeContext = createContext<ModeContextValue>({ mode: 'explore', setMode: () => undefined });

/**
 * Holds the visual theme mode. It only changes colours and motion intensity; it never affects calibration,
 * recommendations or any saved data. It is kept in memory only (nothing is stored in the browser).
 */
export function ModeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ModeKey>('explore');
  useEffect(() => {
    document.documentElement.dataset.mode = mode;
  }, [mode]);
  const value = useMemo(() => ({ mode, setMode }), [mode]);
  return <ModeContext.Provider value={value}>{children}</ModeContext.Provider>;
}

export function useModeTheme(): ModeContextValue {
  return useContext(ModeContext);
}
