import type { Configuration } from '@azure/msal-browser';
import { LogLevel } from '@azure/msal-browser';

// These values come from the Azure AD App Registration for the frontend SPA.
// In development, MSAL is not used — the backend returns a dev user without auth.
export const msalConfig: Configuration = {
  auth: {
    clientId: import.meta.env.VITE_AZURE_CLIENT_ID || 'not-configured',
    authority: `https://login.microsoftonline.com/${import.meta.env.VITE_AZURE_TENANT_ID || 'common'}`,
    redirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: 'sessionStorage',
  },
  system: {
    loggerOptions: {
      logLevel: LogLevel.Warning,
    },
  },
};

// Scope for the backend API — set in Azure AD App Registration (Expose an API)
export const apiScope = import.meta.env.VITE_API_SCOPE || '';

export const isAuthEnabled = Boolean(import.meta.env.VITE_AZURE_CLIENT_ID);
