import type { ReactNode } from 'react';
import { useEffect } from 'react';
import { MsalProvider as MsalReactProvider, useMsal } from '@azure/msal-react';
import { PublicClientApplication } from '@azure/msal-browser';
import { msalConfig, apiScope, isAuthEnabled } from './msalConfig';
import { setAuthToken } from '../api/client';

const msalInstance = new PublicClientApplication(msalConfig);

function TokenAcquirer({ children }: { children: ReactNode }) {
  const { instance, accounts } = useMsal();

  useEffect(() => {
    if (!isAuthEnabled || accounts.length === 0) return;

    instance
      .acquireTokenSilent({
        scopes: [apiScope],
        account: accounts[0],
      })
      .then((response) => {
        setAuthToken(response.accessToken);
      })
      .catch(() => {
        // Silent acquisition failed — trigger interactive login
        instance.acquireTokenPopup({ scopes: [apiScope] }).then((response) => {
          setAuthToken(response.accessToken);
        });
      });
  }, [instance, accounts]);

  return <>{children}</>;
}

export default function AuthProvider({ children }: { children: ReactNode }) {
  if (!isAuthEnabled) {
    // No auth configured — render children directly
    return <>{children}</>;
  }

  return (
    <MsalReactProvider instance={msalInstance}>
      <TokenAcquirer>{children}</TokenAcquirer>
    </MsalReactProvider>
  );
}

export { msalInstance, isAuthEnabled };
