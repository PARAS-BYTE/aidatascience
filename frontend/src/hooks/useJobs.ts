import { useState, useEffect, useCallback } from 'react';
import { Job } from '../types/job';
import { apiService } from '../services/api';

export function useJobs() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiService.getJobs();
      setJobs(data.items);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to fetch jobs';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  const triggerTestJob = async (shouldFail: boolean = false) => {
    try {
      const newJob = await apiService.triggerTestJob(shouldFail);
      setJobs((prev) => [newJob, ...prev]);
      return newJob;
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to trigger job';
      throw new Error(msg);
    }
  };

  return {
    jobs,
    loading,
    error,
    refresh: fetchJobs,
    triggerTestJob,
  };
}
