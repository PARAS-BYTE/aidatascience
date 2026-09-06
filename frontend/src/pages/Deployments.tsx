import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api';
import { 
  Rocket, StopCircle, RefreshCw, ArrowRight, 
  Award, FileText, X, Check, Copy, Code2, Play, Terminal, 
  Sparkles, CheckCircle2, AlertCircle, ChevronDown, 
  ChevronUp, Cpu, Layers, Tag
} from 'lucide-react';

export const Deployments: React.FC = () => {
  const [deployments, setDeployments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCard, setSelectedCard] = useState<any | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  // Per-deployment UI state
  const [snippetTabs, setSnippetTabs] = useState<Record<string, 'json' | 'curl' | 'python' | 'javascript'>>({});
  const [sampleIndices, setSampleIndices] = useState<Record<string, number>>({});
  const [testPayloads, setTestPayloads] = useState<Record<string, string>>({});
  const [testing, setTesting] = useState<Record<string, boolean>>({});
  const [testResults, setTestResults] = useState<Record<string, any>>({});
  const [testErrors, setTestErrors] = useState<Record<string, string | null>>({});
  const [testDurations, setTestDurations] = useState<Record<string, number>>({});
  const [showTester, setShowTester] = useState<Record<string, boolean>>({});
  const [showRawResponse, setShowRawResponse] = useState<Record<string, boolean>>({});

  const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  const apiBaseUrl = isLocal
    ? `${window.location.protocol}//${window.location.hostname}:8000/api/v1`
    : `${window.location.origin}/api/v1`;

  const copySnippet = async (key: string, value: string) => {
    await navigator.clipboard.writeText(value);
    setCopied(key);
    window.setTimeout(() => setCopied(null), 1800);
  };

  const load = () => {
    setLoading(true);
    apiService.getDeployments()
      .then(r => {
        const items = r.items || [];
        setDeployments(items);
        // Pre-fill test payloads for each deployment
        const initialPayloads: Record<string, string> = {};
        items.forEach((d: any) => {
          const sample = getDeploymentSample(d, 0);
          initialPayloads[d.id] = JSON.stringify({ features: sample }, null, 2);
        });
        setTestPayloads(prev => ({ ...initialPayloads, ...prev }));
      })
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const getDeploymentSample = (dep: any, sampleIndex = 0) => {
    if (dep.sample_inputs && dep.sample_inputs[sampleIndex]) {
      return dep.sample_inputs[sampleIndex];
    }
    if (dep.sample_input && Object.keys(dep.sample_input).length > 0) {
      return dep.sample_input;
    }
    if (dep.feature_names && dep.feature_names.length > 0) {
      const fallback: Record<string, any> = {};
      dep.feature_names.forEach((name: string) => {
        const lower = name.toLowerCase();
        if (lower.includes('age')) fallback[name] = 25;
        else if (lower.includes('weight')) fallback[name] = 68.5;
        else if (lower.includes('height')) fallback[name] = 175.0;
        else if (lower.includes('score')) fallback[name] = 7;
        else if (lower.includes('hour')) fallback[name] = 6.0;
        else if (lower.includes('rate') || lower.includes('pct')) fallback[name] = 0.75;
        else if (lower.includes('price') || lower.includes('charge')) fallback[name] = 120.0;
        else fallback[name] = 10;
      });
      return fallback;
    }
    return { feature_1: 10, feature_2: 'Example' };
  };

  const handleSelectSample = (depId: string, dep: any, index: number) => {
    setSampleIndices(prev => ({ ...prev, [depId]: index }));
    const sample = getDeploymentSample(dep, index);
    setTestPayloads(prev => ({
      ...prev,
      [depId]: JSON.stringify({ features: sample }, null, 2)
    }));
  };

  const runLivePrediction = async (dep: any) => {
    const depId = dep.id;
    setTesting(prev => ({ ...prev, [depId]: true }));
    setTestErrors(prev => ({ ...prev, [depId]: null }));
    setTestResults(prev => ({ ...prev, [depId]: null }));
    const startTime = performance.now();

    try {
      const rawText = testPayloads[depId] || JSON.stringify({ features: getDeploymentSample(dep, sampleIndices[depId] || 0) });
      let parsed: any;
      try {
        parsed = JSON.parse(rawText);
      } catch (err: any) {
        throw new Error(`Invalid JSON in request body: ${err.message}`);
      }

      // If wrapper { features: { ... } } is present, use parsed.features, otherwise use parsed directly
      const features = parsed.features ? parsed.features : parsed;
      const result = await apiService.predict(dep.model_id, features);
      const duration = Math.round(performance.now() - startTime);

      setTestDurations(prev => ({ ...prev, [depId]: duration }));
      setTestResults(prev => ({ ...prev, [depId]: result }));
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Prediction request failed';
      setTestErrors(prev => ({ ...prev, [depId]: errorMsg }));
    } finally {
      setTesting(prev => ({ ...prev, [depId]: false }));
    }
  };

  const stopDeployment = async (id: string) => {
    try {
      await apiService.stopDeployment(id);
      load();
    } catch (err: any) { alert(err.response?.data?.detail || 'Failed to stop'); }
  };

  const handlePromote = async (deploymentId: string) => {
    try {
      await apiService.promoteChallenger(deploymentId);
      setActionSuccess('Challenger successfully promoted to Champion!');
      setTimeout(() => setActionSuccess(null), 4000);
      load();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to promote challenger');
    }
  };

  const handleViewModelCard = async (modelId: string) => {
    try {
      const res = await apiService.getModelCard(modelId);
      setSelectedCard(res.content_md);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to load model card');
    }
  };

  const statusColors: Record<string, string> = {
    ACTIVE: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    DEPLOYING: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
    FAILED: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    STOPPED: 'bg-slate-700/30 text-slate-400 border-slate-600/30',
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="animate-fade-in-up flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Rocket className="w-5 h-5 text-sky-400" />
            <span className="text-xs font-semibold text-sky-400 uppercase tracking-wider">Production Serving & Inference</span>
          </div>
          <h1 className="text-3xl font-black text-slate-100 tracking-tight">Deployments & Model APIs</h1>
          <p className="text-sm text-slate-400 mt-1">Real-time model inference endpoints with exact feature schemas, realistic payloads, and 1-click live testing</p>
        </div>
        <button onClick={load} className="p-2.5 text-slate-400 hover:text-slate-200 rounded-xl hover:bg-slate-800/50 border border-slate-800/50 transition-all">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {actionSuccess && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold flex items-center gap-2 animate-fade-in">
          <Check className="w-4 h-4" /> {actionSuccess}
        </div>
      )}

      {loading && (
        <div className="space-y-4 animate-fade-in">
          {[1,2].map(i => <div key={i} className="skeleton h-44 rounded-2xl" />)}
        </div>
      )}

      {!loading && deployments.length > 0 ? (
        <div className="space-y-6">
          {deployments.map((dep, idx) => {
            const isChampion = dep.role === 'champion' || !dep.role;
            const currentTab = snippetTabs[dep.id] || 'json';
            const currentSampleIdx = sampleIndices[dep.id] || 0;
            const sampleInput = getDeploymentSample(dep, currentSampleIdx);
            const totalFeatures = dep.feature_names?.length || Object.keys(sampleInput).length || 0;
            const sampleList = dep.sample_inputs && dep.sample_inputs.length > 0 ? dep.sample_inputs : [sampleInput];
            const isTesterOpen = showTester[dep.id] !== undefined ? showTester[dep.id] : true;
            const isPredicting = testing[dep.id] || false;
            const testResult = testResults[dep.id];
            const testError = testErrors[dep.id];
            const testDuration = testDurations[dep.id];
            const currentPayload = testPayloads[dep.id] !== undefined 
              ? testPayloads[dep.id] 
              : JSON.stringify({ features: sampleInput }, null, 2);

            // Generated code snippets
            const jsonBodyCode = JSON.stringify({ features: sampleInput }, null, 2);
            const curlCode = `curl -X POST "${apiBaseUrl}/models/${dep.model_id}/predict" \\
  -H "Content-Type: application/json" \\
  -d '${JSON.stringify({ features: sampleInput })}'`;

            const pythonCode = `import requests

url = "${apiBaseUrl}/models/${dep.model_id}/predict"
headers = {"Content-Type": "application/json"}
payload = {
    "features": ${JSON.stringify(sampleInput, null, 4).split('\n').join('\n    ')}
}

response = requests.post(url, json=payload, headers=headers)
print("Status:", response.status_code)
print("Prediction Result:", response.json())`;

            const jsCode = `// Send prediction request to deployed model
const response = await fetch("${apiBaseUrl}/models/${dep.model_id}/predict", {
  method: "POST",
  headers: {
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    features: ${JSON.stringify(sampleInput, null, 2).split('\n').join('\n    ')}
  })
});

const result = await response.json();
console.log("Prediction Result:", result);`;

            const activeSnippet = currentTab === 'json' ? jsonBodyCode
              : currentTab === 'curl' ? curlCode
              : currentTab === 'python' ? pythonCode
              : jsCode;

            return (
              <div key={dep.id}
                className={`animate-fade-in-up stagger-${Math.min(idx + 1, 8)} glass-card border border-slate-800/60 rounded-2xl p-6 card-hover transition-all relative overflow-hidden ${
                  dep.status === 'ACTIVE' 
                    ? isChampion ? 'border-amber-500/30 bg-gradient-to-r from-amber-500/5 via-slate-900/40 to-transparent' : 'border-sky-500/30 bg-gradient-to-r from-sky-500/5 via-slate-900/40 to-transparent'
                    : ''
                }`}>
                
                {/* Header row */}
                <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <span className={`px-3 py-1 rounded-xl text-xs font-semibold border ${statusColors[dep.status] || statusColors.STOPPED}`}>
                      {dep.status === 'ACTIVE' && <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1.5 animate-pulse" />}
                      {dep.status}
                    </span>

                    <span className={`px-2.5 py-1 rounded-xl text-xs font-bold flex items-center gap-1.5 border ${
                      isChampion 
                        ? 'bg-amber-500/15 text-amber-300 border-amber-500/40' 
                        : 'bg-sky-500/15 text-sky-300 border-sky-500/40'
                    }`}>
                      <Award className="w-3.5 h-3.5" />
                      {isChampion ? 'Champion' : 'Challenger'}
                    </span>

                    <span className="text-xs text-slate-400 font-mono px-2 py-0.5 rounded-lg bg-slate-900/80 border border-slate-800">
                      Traffic: {Math.round((dep.traffic_pct || 1.0) * 100)}%
                    </span>

                    <span className="text-sm font-bold text-slate-100 flex items-center gap-2">
                      {dep.model_name || `Model v${dep.model_version}`}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleViewModelCard(dep.model_id)}
                      className="text-xs px-3 py-1.5 bg-slate-800/90 text-slate-200 border border-slate-700/60 rounded-xl hover:bg-slate-700 flex items-center gap-1.5 transition-all"
                    >
                      <FileText className="w-3.5 h-3.5 text-sky-400" /> Model Card
                    </button>

                    {!isChampion && dep.status === 'ACTIVE' && (
                      <button
                        onClick={() => handlePromote(dep.id)}
                        className="text-xs px-3 py-1.5 bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-500 hover:to-yellow-500 text-white font-semibold rounded-xl shadow-lg shadow-amber-500/20 flex items-center gap-1 transition-all"
                      >
                        <Award className="w-3.5 h-3.5" /> Promote
                      </button>
                    )}

                    {dep.status === 'ACTIVE' && (
                      <button onClick={() => stopDeployment(dep.id)}
                        className="text-xs px-3 py-1.5 bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded-xl hover:bg-rose-500/20 flex items-center gap-1 transition-all">
                        <StopCircle className="w-3 h-3" /> Stop
                      </button>
                    )}
                  </div>
                </div>

                {/* Model Metadata Tags */}
                <div className="flex items-center gap-2 flex-wrap mb-4">
                  {dep.algorithm && (
                    <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-lg bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                      <Cpu className="w-3.5 h-3.5 text-indigo-400" /> {dep.algorithm.replace(/_/g, ' ').toUpperCase()}
                    </span>
                  )}
                  {dep.task_type && (
                    <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-lg bg-sky-500/10 text-sky-300 border border-sky-500/20">
                      <Layers className="w-3.5 h-3.5 text-sky-400" /> {dep.task_type.replace(/_/g, ' ')}
                    </span>
                  )}
                  {dep.target_column && (
                    <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-lg bg-purple-500/10 text-purple-300 border border-purple-500/20">
                      <Tag className="w-3.5 h-3.5 text-purple-400" /> Target: <strong className="font-semibold text-purple-200">{dep.target_column}</strong>
                    </span>
                  )}
                  <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                    <Sparkles className="w-3.5 h-3.5 text-emerald-400" /> {totalFeatures} Real Features Expected
                  </span>
                </div>

                {/* Status KPI Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-5">
                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/40">
                    <p className="text-[10px] text-slate-400 uppercase font-medium">Production Endpoint</p>
                    <p className="text-xs text-sky-400 font-mono truncate mt-1 flex items-center gap-1">
                      POST /models/{dep.model_id.slice(0, 8)}.../predict
                    </p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/40">
                    <p className="text-[10px] text-slate-400 uppercase font-medium">Inference Requests Served</p>
                    <p className="text-base text-slate-100 font-mono mt-0.5 font-bold">{(dep.request_count || 0).toLocaleString()}</p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/40">
                    <p className="text-[10px] text-slate-400 uppercase font-medium">Deployed On</p>
                    <p className="text-xs text-slate-300 mt-1">{new Date(dep.created_at).toLocaleString()}</p>
                  </div>
                </div>

                {/* Real Model API Documentation & Snippet Generator */}
                <div className="rounded-xl border border-slate-800/80 bg-slate-950/70 p-4 space-y-4">
                  <div className="flex items-center justify-between flex-wrap gap-2 pb-3 border-b border-slate-800/70">
                    <div className="flex items-center gap-2">
                      <Code2 className="w-4 h-4 text-sky-400" />
                      <div>
                        <h3 className="text-sm font-bold text-slate-100">Live Model API Integration</h3>
                        <p className="text-xs text-slate-400">
                          Send a POST request containing this model's exact expected features.
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => copySnippet(`url-${dep.id}`, `${apiBaseUrl}/models/${dep.model_id}/predict`)}
                        className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700/50 transition-all font-mono"
                      >
                        {copied === `url-${dep.id}` ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-slate-400" />}
                        Copy Endpoint URL
                      </button>
                    </div>
                  </div>

                  {/* Endpoint Bar */}
                  <div className="flex items-center justify-between rounded-lg bg-slate-900/90 border border-slate-800 px-3.5 py-2 overflow-x-auto gap-3">
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-mono">POST</span>
                      <code className="text-xs text-slate-200 font-mono">{apiBaseUrl}/models/{dep.model_id}/predict</code>
                    </div>
                    <span className="text-[11px] text-slate-400 hidden sm:inline">Content-Type: application/json</span>
                  </div>

                  {/* Sample Row Picker */}
                  {sampleList.length > 1 && (
                    <div className="flex items-center gap-2 flex-wrap pt-1">
                      <span className="text-xs text-slate-400 font-medium">Real Dataset Samples:</span>
                      {sampleList.map((_: any, sIdx: number) => (
                        <button
                          key={sIdx}
                          onClick={() => handleSelectSample(dep.id, dep, sIdx)}
                          className={`text-xs px-3 py-1 rounded-lg font-medium transition-all ${
                            currentSampleIdx === sIdx
                              ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 shadow-sm shadow-sky-500/10'
                              : 'bg-slate-900/80 text-slate-400 border border-slate-800 hover:text-slate-200'
                          }`}
                        >
                          Sample Record #{sIdx + 1}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Code Tabs Header */}
                  <div className="flex items-center justify-between flex-wrap gap-2 border-b border-slate-800/60 pb-2">
                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => setSnippetTabs(prev => ({ ...prev, [dep.id]: 'json' }))}
                        className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-all flex items-center gap-1.5 ${
                          currentTab === 'json'
                            ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40'
                            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
                        }`}
                      >
                        <FileText className="w-3.5 h-3.5" /> Request Body (JSON)
                      </button>
                      <button
                        onClick={() => setSnippetTabs(prev => ({ ...prev, [dep.id]: 'curl' }))}
                        className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-all flex items-center gap-1.5 ${
                          currentTab === 'curl'
                            ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40'
                            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
                        }`}
                      >
                        <Terminal className="w-3.5 h-3.5" /> cURL
                      </button>
                      <button
                        onClick={() => setSnippetTabs(prev => ({ ...prev, [dep.id]: 'python' }))}
                        className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-all flex items-center gap-1.5 ${
                          currentTab === 'python'
                            ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40'
                            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
                        }`}
                      >
                        <Code2 className="w-3.5 h-3.5" /> Python (requests)
                      </button>
                      <button
                        onClick={() => setSnippetTabs(prev => ({ ...prev, [dep.id]: 'javascript' }))}
                        className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-all flex items-center gap-1.5 ${
                          currentTab === 'javascript'
                            ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40'
                            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
                        }`}
                      >
                        <Code2 className="w-3.5 h-3.5" /> JavaScript (fetch)
                      </button>
                    </div>

                    <button
                      onClick={() => copySnippet(`snippet-${dep.id}-${currentTab}`, activeSnippet)}
                      className="inline-flex items-center gap-1.5 text-xs px-3 py-1 rounded-lg bg-sky-500/10 hover:bg-sky-500/20 text-sky-300 border border-sky-500/30 transition-all font-medium"
                    >
                      {copied === `snippet-${dep.id}-${currentTab}` ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      Copy Code
                    </button>
                  </div>

                  {/* Code Box */}
                  <div className="relative rounded-xl bg-slate-950 border border-slate-800/80 p-3.5 overflow-hidden">
                    <pre className="text-xs font-mono text-slate-200 leading-relaxed overflow-x-auto max-h-64 scrollbar-thin">
                      {activeSnippet}
                    </pre>
                  </div>

                  {/* Interactive Live Tester Section */}
                  <div className="pt-2">
                    <button
                      onClick={() => setShowTester(prev => ({ ...prev, [dep.id]: !isTesterOpen }))}
                      className="flex items-center justify-between w-full p-2 rounded-lg bg-slate-900/60 hover:bg-slate-900 border border-slate-800/50 text-xs font-semibold text-slate-200 transition-all"
                    >
                      <div className="flex items-center gap-2">
                        <Play className="w-3.5 h-3.5 text-emerald-400" />
                        <span>Interactive Live Inference Tester (Test this model directly)</span>
                      </div>
                      {isTesterOpen ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                    </button>

                    {isTesterOpen && (
                      <div className="mt-3 p-4 rounded-xl bg-slate-900/80 border border-slate-800/80 space-y-4 animate-fade-in">
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <p className="text-xs text-slate-300">
                            Edit feature values below and click <strong>Send Live Prediction</strong> to execute real inference on this deployment:
                          </p>
                          <button
                            onClick={() => handleSelectSample(dep.id, dep, currentSampleIdx)}
                            className="text-[11px] text-sky-400 hover:text-sky-300 underline font-medium"
                          >
                            Reset to Original Sample
                          </button>
                        </div>

                        <div>
                          <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1.5">
                            POST Payload (JSON with <code>features</code> object)
                          </label>
                          <textarea
                            value={currentPayload}
                            onChange={(e) => setTestPayloads(prev => ({ ...prev, [dep.id]: e.target.value }))}
                            rows={8}
                            className="w-full font-mono text-xs bg-slate-950 border border-slate-700/80 text-sky-300 rounded-xl p-3 focus:outline-none focus:ring-1 focus:ring-sky-500 transition-all resize-y"
                            placeholder='{"features": { ... }}'
                          />
                        </div>

                        <div className="flex items-center gap-3">
                          <button
                            onClick={() => runLivePrediction(dep)}
                            disabled={isPredicting}
                            className="px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-emerald-500/20 flex items-center gap-2 transition-all disabled:opacity-50"
                          >
                            {isPredicting ? (
                              <>
                                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                                Computing Prediction...
                              </>
                            ) : (
                              <>
                                <Play className="w-3.5 h-3.5 fill-current" />
                                Send Live Prediction
                              </>
                            )}
                          </button>

                          {testDuration !== undefined && (
                            <span className="text-xs font-mono text-emerald-400 px-2 py-1 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                              ⚡ Latency: {testDuration}ms
                            </span>
                          )}
                        </div>

                        {/* Error output */}
                        {testError && (
                          <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-start gap-2 animate-fade-in">
                            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                            <div>
                              <p className="font-semibold">Prediction Error</p>
                              <p className="mt-0.5 font-mono">{testError}</p>
                            </div>
                          </div>
                        )}

                        {/* Live Prediction Result Card */}
                        {testResult && (
                          <div className="p-4 rounded-xl bg-gradient-to-br from-slate-950 to-slate-900 border border-emerald-500/30 space-y-3 animate-fade-in">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2 text-emerald-400">
                                <CheckCircle2 className="w-4 h-4" />
                                <span className="text-xs font-bold uppercase tracking-wider">Prediction Succeeded (200 OK)</span>
                              </div>
                              <button
                                onClick={() => setShowRawResponse(prev => ({ ...prev, [dep.id]: !prev[dep.id] }))}
                                className="text-[11px] text-slate-400 hover:text-slate-200 underline"
                              >
                                {showRawResponse[dep.id] ? 'Hide Raw JSON' : 'Show Raw JSON'}
                              </button>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                              <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800">
                                <p className="text-[10px] uppercase font-bold text-slate-400">
                                  Predicted {dep.target_column ? `Target (${dep.target_column})` : 'Value'}
                                </p>
                                <p className="text-xl font-black text-emerald-300 mt-1 font-mono">
                                  {String(testResult.prediction)}
                                </p>
                              </div>

                              {testResult.probability !== null && testResult.probability !== undefined && (
                                <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800">
                                  <p className="text-[10px] uppercase font-bold text-slate-400">Confidence / Probability</p>
                                  <p className="text-xl font-black text-sky-400 mt-1 font-mono">
                                    {(testResult.probability * 100).toFixed(1)}%
                                  </p>
                                </div>
                              )}
                            </div>

                            {showRawResponse[dep.id] && (
                              <div className="mt-2 pt-2 border-t border-slate-800">
                                <pre className="p-3 rounded-lg bg-slate-950 text-[11px] font-mono text-emerald-300 overflow-x-auto">
                                  {JSON.stringify(testResult, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : !loading ? (
        <div className="animate-fade-in-up glass-card border border-slate-800/50 rounded-2xl p-16 text-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center mx-auto animate-float">
            <Rocket className="w-8 h-8 text-sky-400/60" />
          </div>
          <h3 className="text-xl font-bold text-slate-200">No Active Deployments</h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto">Deploy models from the Model Registry to start serving live predictions</p>
          <div className="flex items-center justify-center gap-2 text-sky-400">
            <ArrowRight className="w-4 h-4" />
            <span className="text-sm font-medium">Go to Models to deploy</span>
          </div>
        </div>
      ) : null}

      {/* Model Card Modal */}
      {selectedCard && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-700/80 rounded-2xl p-6 max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-sky-400" />
                <h3 className="text-base font-bold text-slate-100">Standardized Model Card</h3>
              </div>
              <button onClick={() => setSelectedCard(null)} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="overflow-y-auto flex-1 pr-2 space-y-4 text-slate-300 text-xs leading-relaxed font-sans">
              <pre className="whitespace-pre-wrap font-sans bg-slate-950/60 p-4 rounded-xl border border-slate-800 text-slate-300">
                {selectedCard}
              </pre>
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-800 mt-2">
              <button
                onClick={() => setSelectedCard(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
