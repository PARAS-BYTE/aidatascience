import React, { useState } from 'react';
import { useJobs } from '../hooks/useJobs';
import { JobStatusBadge } from '../components/JobStatusBadge';
import { formatDate } from '../utils/formatters';
import { Activity, RefreshCw, Play, AlertOctagon, CheckCircle2 } from 'lucide-react';

export const Jobs: React.FC = () => {
  const { jobs, loading, refresh, triggerTestJob } = useJobs();
  const [triggering, setTriggering] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const handleTrigger = async (shouldFail: boolean = false) => {
    setTriggering(true);
    setToast(null);
    try {
      const newJob = await triggerTestJob(shouldFail);
      setToast(`Test job created (ID: ${newJob.id.slice(0, 8)}...). Refreshing status...`);
      setTimeout(() => refresh(), 4500);
    } catch (err: any) {
      setToast(`Failed to launch job: ${err.message}`);
    } finally {
      setTriggering(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">Job Infrastructure</h1>
          <p className="text-slate-400 text-sm mt-1">
            Monitor and test execution states (PENDING, RUNNING, COMPLETED, FAILED)
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => handleTrigger(false)}
            disabled={triggering}
            className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-sky-600 hover:bg-sky-500 rounded-xl shadow-lg shadow-sky-900/20 transition-colors disabled:opacity-50"
          >
            <Play className="w-4 h-4" />
            Trigger Test Job
          </button>
          <button
            onClick={() => handleTrigger(true)}
            disabled={triggering}
            className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-rose-300 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 rounded-xl transition-colors disabled:opacity-50"
          >
            <AlertOctagon className="w-4 h-4" />
            Simulate Fail Job
          </button>
          <button
            onClick={refresh}
            disabled={loading}
            className="p-2.5 text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl transition-colors disabled:opacity-50"
            title="Refresh Jobs"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {toast && (
        <div className="p-4 rounded-xl bg-sky-500/10 border border-sky-500/20 text-sky-400 text-sm flex items-center gap-2 animate-in fade-in duration-200">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <span>{toast}</span>
        </div>
      )}

      {/* Jobs Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        {jobs.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <Activity className="w-12 h-12 text-slate-600 mx-auto" />
            <p className="text-slate-400 text-sm font-medium">No jobs recorded yet.</p>
            <p className="text-slate-500 text-xs">Click 'Trigger Test Job' above to validate job state transitions.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-800/60 text-slate-400 text-xs uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="px-6 py-3.5 font-medium">Job ID</th>
                  <th className="px-6 py-3.5 font-medium">Job Type</th>
                  <th className="px-6 py-3.5 font-medium">Status</th>
                  <th className="px-6 py-3.5 font-medium">Created At</th>
                  <th className="px-6 py-3.5 font-medium">Completed At</th>
                  <th className="px-6 py-3.5 font-medium">Result / Error</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {jobs.map((job) => (
                  <tr key={job.id} className="hover:bg-slate-800/40 transition-colors font-mono text-xs">
                    <td className="px-6 py-4 text-sky-400 font-semibold">{job.id.slice(0, 8)}...</td>
                    <td className="px-6 py-4 text-slate-200">{job.job_type}</td>
                    <td className="px-6 py-4">
                      <JobStatusBadge status={job.status} />
                    </td>
                    <td className="px-6 py-4 text-slate-400">{formatDate(job.created_at)}</td>
                    <td className="px-6 py-4 text-slate-400">{formatDate(job.completed_at)}</td>
                    <td className="px-6 py-4 max-w-xs truncate">
                      {job.error_message ? (
                        <span className="text-rose-400">{job.error_message}</span>
                      ) : job.result_path ? (
                        <span className="text-emerald-400">{job.result_path}</span>
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
