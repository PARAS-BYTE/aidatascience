import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { MainLayout } from './layouts/MainLayout';
import { Dashboard } from './pages/Dashboard';
import { Datasets } from './pages/Datasets';
import { DatasetDetails } from './pages/DatasetDetails';
import { EDA } from './pages/EDA';
import { Cleaning } from './pages/Cleaning';
import { FeatureEngineering } from './pages/FeatureEngineering';
import { Experiments } from './pages/Experiments';
import { Models } from './pages/Models';
import { Explainability } from './pages/Explainability';
import { AIChat } from './pages/AIChat';
import { MultiAgentStudio } from './pages/MultiAgentStudio';
import { Deployments } from './pages/Deployments';
import { Monitoring } from './pages/Monitoring';
import { Jobs } from './pages/Jobs';
import { Settings } from './pages/Settings';
import { AskData } from './pages/AskData';
import { Forecasting } from './pages/Forecasting';
import { Profile } from './pages/Profile';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="profile" element={<Profile />} />
          <Route path="datasets" element={<Datasets />} />
          <Route path="datasets/:id" element={<DatasetDetails />} />
          <Route path="eda" element={<EDA />} />
          <Route path="ask-data" element={<AskData />} />
          <Route path="cleaning" element={<Cleaning />} />
          <Route path="feature-engineering" element={<FeatureEngineering />} />
          <Route path="experiments" element={<Experiments />} />
          <Route path="models" element={<Models />} />
          <Route path="forecasting" element={<Forecasting />} />
          <Route path="explainability" element={<Explainability />} />
          <Route path="multi-agent" element={<MultiAgentStudio />} />
          <Route path="ai-chat" element={<AIChat />} />
          <Route path="deployments" element={<Deployments />} />
          <Route path="monitoring" element={<Monitoring />} />
          <Route path="jobs" element={<Jobs />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
