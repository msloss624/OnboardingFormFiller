import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import { MsalProvider as MsalReactProvider, useMsal } from '@azure/msal-react';
import { PublicClientApplication } from '@azure/msal-browser';
import { msalConfig, apiScope, isAuthEnabled } from './msalConfig';
import { setAuthToken, setTokenAcquirer } from '../api/client';

const msalInstance = new PublicClientApplication(msalConfig);
// MSAL v5 requires explicit initialization before any operations
const msalReady = isAuthEnabled ? msalInstance.initialize() : Promise.resolve();

function TokenAcquirer({ children }: { children: ReactNode }) {
  const { instance, accounts } = useMsal();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!isAuthEnabled) {
      setReady(true);
      return;
    }

    msalReady
      .then(() => instance.handleRedirectPromise())
      .then((response) => {
        if (response) {
          setAuthToken(response.accessToken);
        }

        const currentAccounts = instance.getAllAccounts();
        if (currentAccounts.length > 0) {
          // Register interceptor that gets a fresh token for every API call
          setTokenAcquirer(async () => {
            const resp = await instance.acquireTokenSilent({
              scopes: [apiScope],
              account: currentAccounts[0],
            });
            return resp.accessToken;
          });
          setReady(true);
        } else {
          return instance.acquireTokenRedirect({ scopes: [apiScope] });
        }
      })
      .catch((err) => {
        console.error('MSAL auth error:', err);
      });
  }, [instance, accounts]);

  if (!ready) return null;
  return <>{children}</>;
}

export default function AuthProvider({ children }: { children: ReactNode }) {
  if (!isAuthEnabled) {
    return <>{children}</>;
  }

  return (
    <MsalReactProvider instance={msalInstance}>
      <TokenAcquirer>{children}</TokenAcquirer>
    </MsalReactProvider>
  );
}

export { msalInstance, isAuthEnabled };
