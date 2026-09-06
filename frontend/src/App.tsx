import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
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
import { Forecasting } from './pages/Forecasting';
import { Profile } from './pages/Profile';
import { Projects } from './pages/Projects';
import { ProjectDetails } from './pages/ProjectDetails';

import { DataQuality } from './pages/DataQuality';
import { Unsupervised } from './pages/Unsupervised';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="projects" element={<Projects />} />
          <Route path="projects/:id" element={<ProjectDetails />} />
          <Route path="profile" element={<Profile />} />
          <Route path="datasets" element={<Datasets />} />
          <Route path="datasets/:id" element={<DatasetDetails />} />
          <Route path="eda" element={<EDA />} />
          <Route path="data-quality" element={<DataQuality />} />
          <Route path="ask-data" element={<Navigate to="/ai-chat?mode=ask-data" replace />} />
          <Route path="cleaning" element={<Cleaning />} />
          <Route path="feature-engineering" element={<FeatureEngineering />} />
          <Route path="experiments" element={<Experiments />} />
          <Route path="models" element={<Models />} />
          <Route path="unsupervised" element={<Unsupervised />} />
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
