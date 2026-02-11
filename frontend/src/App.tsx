import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { useMsal } from '@azure/msal-react';
import AuthProvider, { isAuthEnabled } from './auth/MsalProvider';
import SearchPage from './pages/SearchPage';
import GatherPage from './pages/GatherPage';
import ExtractingPage from './pages/ExtractingPage';
import ReviewPage from './pages/ReviewPage';
import SendEmailPage from './pages/SendEmailPage';
import HistoryPage from './pages/HistoryPage';

const steps = [
  { path: '/', label: 'Search' },
  { path: '/gather', label: 'Gather Data' },
  { path: '/extracting', label: 'Extract' },
  { path: '/review', label: 'Review & Export' },
  { path: '/send', label: 'Send' },
];

function StepIndicator() {
  const location = useLocation();
  const isHistory = location.pathname === '/history';
  const currentIdx = steps.findIndex((s) =>
    s.path === '/' ? location.pathname === '/' : location.pathname.startsWith(s.path)
  );

  if (isHistory) return null;

  return (
    <div className="bg-white border-b border-gray-200">
      <div className="max-w-6xl mx-auto flex items-center justify-center gap-0 py-3">
        {steps.map((step, i) => {
          const isCompleted = i < currentIdx;
          const isActive = i === currentIdx;
          return (
            <div key={step.path} className="flex items-center">
              <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm transition-colors ${
                isCompleted ? 'text-accent-dark' : isActive ? 'text-primary font-semibold' : 'text-gray-400'
              }`}>
                <span className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold transition-colors ${
                  isCompleted ? 'bg-accent text-white' : isActive ? 'bg-primary text-white' : 'bg-gray-200 text-gray-500'
                }`}>
                  {isCompleted ? '\u2713' : i + 1}
                </span>
                {step.label}
              </div>
              {i < steps.length - 1 && (
                <div className={`mx-3 h-0.5 w-14 transition-colors ${
                  isCompleted ? 'bg-accent' : isActive ? 'bg-primary' : 'bg-gray-200'
                }`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function UserName() {
  if (!isAuthEnabled) return null;
  const { accounts } = useMsal();
  const name = accounts[0]?.name?.split(' ')[0];
  if (!name) return null;
  return <span className="text-sm text-white/75">{name}</span>;
}

function Layout() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-bw-blue text-white px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src="/bellwether-logo.png" alt="Bellwether" className="h-9 w-9" />
            <h1 className="font-heading text-xl tracking-wide">Onboarding Form Filler</h1>
          </div>
          <div className="flex items-center gap-4">
            <UserName />
            <Link to="/history" className="text-sm text-white/75 hover:text-white transition-colors">
              History
            </Link>
          </div>
        </div>
      </header>

      <StepIndicator />

      {/* Main content */}
      <main className="max-w-6xl mx-auto px-4 py-8 pb-12">
        <Routes>
          <Route path="/" element={<SearchPage />} />
          <Route path="/gather" element={<GatherPage />} />
          <Route path="/extracting/:runId" element={<ExtractingPage />} />
          <Route path="/review/:runId" element={<ReviewPage />} />
          <Route path="/send/:runId" element={<SendEmailPage />} />
          <Route path="/history" element={<HistoryPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Layout />
      </BrowserRouter>
    </AuthProvider>
  );
}
