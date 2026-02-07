import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import AuthProvider from './auth/MsalProvider';
import SearchPage from './pages/SearchPage';
import GatherPage from './pages/GatherPage';
import ExtractingPage from './pages/ExtractingPage';
import ReviewPage from './pages/ReviewPage';
import HistoryPage from './pages/HistoryPage';

const steps = [
  { path: '/', label: 'Search' },
  { path: '/gather', label: 'Gather Data' },
  { path: '/extracting', label: 'Extract' },
  { path: '/review', label: 'Review & Export' },
];

function StepIndicator() {
  const location = useLocation();
  const currentIdx = steps.findIndex((s) =>
    s.path === '/' ? location.pathname === '/' : location.pathname.startsWith(s.path)
  );

  return (
    <div className="flex items-center justify-center gap-0 py-4">
      {steps.map((step, i) => {
        const isCompleted = i < currentIdx;
        const isActive = i === currentIdx;
        return (
          <div key={step.path} className="flex items-center">
            <div className={`flex items-center gap-2 px-3 py-1 text-sm ${
              isCompleted ? 'text-green-600' : isActive ? 'text-[#1E4488] font-semibold' : 'text-gray-400'
            }`}>
              <span className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${
                isCompleted ? 'bg-green-500 text-white' : isActive ? 'bg-[#1E4488] text-white' : 'bg-gray-200 text-gray-500'
              }`}>
                {isCompleted ? '\u2713' : i + 1}
              </span>
              {step.label}
            </div>
            {i < steps.length - 1 && (
              <div className={`mx-2 h-0.5 w-10 ${isCompleted ? 'bg-green-500' : 'bg-gray-200'}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

function Layout() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-[#1E4488] to-[#2a5298] text-white px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">Onboarding Form Filler</h1>
            <p className="text-sm text-white/75">Auto-fill onboarding forms from HubSpot deals and Fireflies transcripts</p>
          </div>
          <Link to="/history" className="text-sm text-white/75 hover:text-white">
            History
          </Link>
        </div>
      </header>

      <StepIndicator />

      {/* Main content */}
      <main className="max-w-5xl mx-auto px-4 pb-12">
        <Routes>
          <Route path="/" element={<SearchPage />} />
          <Route path="/gather" element={<GatherPage />} />
          <Route path="/extracting/:runId" element={<ExtractingPage />} />
          <Route path="/review/:runId" element={<ReviewPage />} />
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
