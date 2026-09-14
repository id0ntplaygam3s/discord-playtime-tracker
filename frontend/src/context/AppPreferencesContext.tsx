import { createContext, useContext } from 'react';
import type { ReactNode } from 'react';

interface AppPreferencesContextValue {
  autoRefreshEnabled: boolean;
}

const AppPreferencesContext = createContext<AppPreferencesContextValue>({
  autoRefreshEnabled: true,
});

export function AppPreferencesProvider({
  value,
  children,
}: {
  value: AppPreferencesContextValue;
  children: ReactNode;
}) {
  return <AppPreferencesContext.Provider value={value}>{children}</AppPreferencesContext.Provider>;
}

export function useAppPreferences() {
  return useContext(AppPreferencesContext);
}
