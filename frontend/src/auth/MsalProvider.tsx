import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import { MsalProvider as MsalReactProvider, useMsal } from '@azure/msal-react';
import { PublicClientApplication, InteractionRequiredAuthError } from '@azure/msal-browser';
import { msalConfig, apiScope, isAuthEnabled } from './msalConfig';
import { setAuthToken } from '../api/client';

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
          setReady(true);
          return;
        }

        if (accounts.length > 0) {
          return instance
            .acquireTokenSilent({
              scopes: [apiScope],
              account: accounts[0],
            })
            .then((resp) => {
              setAuthToken(resp.accessToken);
              setReady(true);
            })
            .catch((error) => {
              if (error instanceof InteractionRequiredAuthError) {
                return instance.acquireTokenRedirect({ scopes: [apiScope] });
              }
            });
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
