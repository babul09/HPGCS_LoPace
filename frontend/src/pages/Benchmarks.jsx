import React, { useEffect, useMemo, useState } from 'react';
import { TrendingUp, FilePieChart, Target } from 'lucide-react';

export default function Benchmarks() {
  const [resultsDoc, setResultsDoc] = useState(null);
  const [resultPath, setResultPath] = useState('evaluation_results.json');
  const [selectedType, setSelectedType] = useState('all');
  const [selectedExperiment, setSelectedExperiment] = useState('');
  const [dictOverheadMode, setDictOverheadMode] = useState('with');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const methodOrder = [
    'zstd', 'gzip', 'brotli', 'cascade', 'hybrid', 'zstd_dict',
    'corpus_dedup', 'corpus_dedup_chunked', 'delta', 'adaptive'
  ];

  const baselineKeys = ['zstd', 'gzip', 'brotli', 'cascade', 'hybrid', 'zstd_dict'];

  const getMethodAlias = (key) => {
    switch (key) {
      case 'zstd': return 'Per-prompt Zstd';
      case 'gzip': return 'Gzip/DEFLATE (best level)';
      case 'brotli': return 'Brotli (best quality)';
      case 'cascade': return 'Hybrid Cascade (best)';
      case 'hybrid': return 'Per-prompt Hybrid';
      case 'zstd_dict': return `Zstd + Dictionary (${dictOverheadMode === 'with' ? 'with' : 'without'} overhead)`;
      case 'zstd_dictionary': return `Zstd + Dictionary (${dictOverheadMode === 'with' ? 'with' : 'without'} overhead)`;
      case 'corpus_dedup': return 'Corpus Dedup';
      case 'corpus_dedup_chunked': return 'Corpus Dedup (chunked)';
      case 'delta': return 'Delta Compression';
      case 'adaptive': return 'Adaptive Router';
      default: return key;
    }
  };

  const getRunType = (name) => {
    if (name?.startsWith('Synthetic:')) return 'synthetic';
    if (name?.startsWith('Real:')) return 'real';
    return 'other';
  };

  const loadResultsFromFile = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/benchmark-results?path=${encodeURIComponent(resultPath)}`);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || 'Failed to load benchmark results file');
      }

      setResultsDoc(payload.results);
      const firstExperiment = payload.results?.experiments?.[0]?.experiment || '';
      setSelectedExperiment(firstExperiment);
    } catch (err) {
      setError(err.message);
      setResultsDoc(null);
      setSelectedExperiment('');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadResultsFromFile();
  }, []);

  const experiments = useMemo(() => resultsDoc?.experiments || [], [resultsDoc]);

  const filteredExperiments = useMemo(() => {
    if (selectedType === 'all') return experiments;
    return experiments.filter((entry) => getRunType(entry.experiment) === selectedType);
  }, [experiments, selectedType]);

  useEffect(() => {
    if (!filteredExperiments.find((entry) => entry.experiment === selectedExperiment)) {
      setSelectedExperiment(filteredExperiments[0]?.experiment || '');
    }
  }, [filteredExperiments, selectedExperiment]);

  const activeExperiment = useMemo(() => {
    return filteredExperiments.find((entry) => entry.experiment === selectedExperiment) || null;
  }, [filteredExperiments, selectedExperiment]);

  const methodRows = useMemo(() => {
    if (!activeExperiment?.methods) return [];
    const entries = Object.entries(activeExperiment.methods)
      .filter(([key]) => !key.endsWith('_sweep'))
      .map(([key, method]) => {
        const selectedStrategy = method.selected_strategy;
        const isDictionaryResult = key === 'zstd_dict'
          || key === 'zstd_dictionary'
          || (key === 'adaptive' && ['zstd_dict', 'zstd_dictionary'].includes(selectedStrategy));

        const totalOriginal = Number(method.total_original ?? 0);
        const totalCompressed = Number(method.total_compressed ?? 0);
        const totalWithOverhead = Number(method.total_with_dict_overhead ?? totalCompressed);
        const withOverhead = dictOverheadMode === 'with';

        const stored = isDictionaryResult
          ? (withOverhead ? totalWithOverhead : totalCompressed)
          : Number(method.total_compressed ?? method.total_with_dict_overhead ?? 0);

        const ratio = isDictionaryResult
          ? Number(
            withOverhead
              ? (method.ratio_with_dict ?? (stored ? totalOriginal / stored : 0))
              : (method.ratio_without_dict ?? (stored ? totalOriginal / stored : 0))
          )
          : Number(method.ratio ?? method.ratio_with_dict ?? 0);

        const savings = isDictionaryResult
          ? Number(totalOriginal ? (1 - stored / totalOriginal) * 100 : 0)
          : Number(method.savings_pct ?? 0);

        return {
          key,
          name: getMethodAlias(key),
          stored,
          ratio,
          savings,
          isDictionaryResult,
          selectedStrategyLabel: selectedStrategy ? getMethodAlias(selectedStrategy) : '',
          error: method.error,
          raw: method,
        };
      });

    return entries.sort((a, b) => {
      const ia = methodOrder.indexOf(a.key);
      const ib = methodOrder.indexOf(b.key);
      const oa = ia === -1 ? Number.MAX_SAFE_INTEGER : ia;
      const ob = ib === -1 ? Number.MAX_SAFE_INTEGER : ib;
      return oa - ob;
    });
  }, [activeExperiment, dictOverheadMode]);

  const zstdStored = methodRows.find((row) => row.key === 'zstd')?.stored || 0;
  const bestOverall = methodRows.filter((row) => !row.error).sort((a, b) => b.ratio - a.ratio)[0];
  const bestBaseline = methodRows
    .filter((row) => !row.error && baselineKeys.includes(row.key))
    .sort((a, b) => b.ratio - a.ratio)[0];
  const dedupRow = methodRows.find((row) => row.key === 'corpus_dedup');
  const sweeps = activeExperiment?.methods || {};

  return (
    <div className="benchmarks-container" style={{ animation: 'fadeIn 0.5s ease' }}>
      <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
        <h1 className="display-large" style={{ color: 'var(--md-sys-color-primary)' }}>Benchmark Results</h1>
        <p className="headline-large" style={{ color: 'var(--md-sys-color-secondary)' }}>Comprehensive evaluation across synthetic and real-world LLM prompt corpora</p>
      </div>

      <div className="material-card" style={{ marginBottom: '2rem' }}>
        <h2 className="headline-large" style={{ marginBottom: '1rem' }}>Load Results File</h2>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '1rem', alignItems: 'end' }}>
          <div>
            <label className="label-large" style={{ display: 'block', marginBottom: '0.5rem' }}>Results JSON path</label>
            <input
              type="text"
              value={resultPath}
              onChange={(e) => setResultPath(e.target.value)}
              style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--md-sys-color-outline-variant)', background: 'var(--md-sys-color-surface)' }}
            />
          </div>
          <div>
            <label className="label-large" style={{ display: 'block', marginBottom: '0.5rem' }}>Run type</label>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--md-sys-color-outline-variant)', background: 'var(--md-sys-color-surface)' }}
            >
              <option value="all">All</option>
              <option value="synthetic">Synthetic</option>
              <option value="real">Real</option>
              <option value="other">Other</option>
            </select>
          </div>
          <button
            className="material-button-primary"
            onClick={loadResultsFromFile}
            disabled={loading}
            style={{ justifyContent: 'center' }}
          >
            {loading ? 'Loading...' : 'Load File'}
          </button>
        </div>

        {filteredExperiments.length > 0 && (
          <div style={{ marginTop: '1rem' }}>
            <label className="label-large" style={{ display: 'block', marginBottom: '0.5rem' }}>Experiment</label>
            <select
              value={selectedExperiment}
              onChange={(e) => setSelectedExperiment(e.target.value)}
              style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--md-sys-color-outline-variant)', background: 'var(--md-sys-color-surface)' }}
            >
              {filteredExperiments.map((entry) => (
                <option key={entry.experiment} value={entry.experiment}>{entry.experiment}</option>
              ))}
            </select>
          </div>
        )}

        <div style={{ marginTop: '1rem' }}>
          <label className="label-large" style={{ display: 'block', marginBottom: '0.5rem' }}>Dictionary metric view</label>
          <select
            value={dictOverheadMode}
            onChange={(e) => setDictOverheadMode(e.target.value)}
            style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--md-sys-color-outline-variant)', background: 'var(--md-sys-color-surface)' }}
          >
            <option value="with">With overhead (deployment realistic)</option>
            <option value="without">Without overhead (raw compression only)</option>
          </select>
        </div>

        {error && (
          <p style={{ color: 'var(--md-sys-color-error)', marginTop: '1rem' }}>{error}</p>
        )}
      </div>

      <div className="material-card" style={{ marginBottom: '3rem', padding: '0', overflow: 'hidden' }}>
        <div style={{ padding: '2rem', background: 'var(--md-sys-color-primary-container)' }}>
          <h2 className="headline-large" style={{ color: 'var(--md-sys-color-on-primary-container)' }}>
            Method Comparison {activeExperiment ? `(${activeExperiment.experiment})` : ''}
          </h2>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
             <thead>
               <tr style={{ background: 'var(--md-sys-color-surface-container-high)', borderBottom: '2px solid var(--md-sys-color-outline-variant)' }}>
                 <th style={{ padding: '1rem 2rem' }}>Method</th>
                 <th style={{ padding: '1rem 2rem' }}>Total Stored</th>
                 <th style={{ padding: '1rem 2rem' }}>Ratio</th>
                 <th style={{ padding: '1rem 2rem' }}>Savings</th>
                 <th style={{ padding: '1rem 2rem' }}>Advantage</th>
               </tr>
             </thead>
             <tbody>
               {methodRows.length === 0 && (
                 <tr>
                   <td colSpan={5} style={{ padding: '1rem 2rem', color: 'var(--md-sys-color-outline)' }}>Load a results file to view benchmark methods.</td>
                 </tr>
               )}
               {methodRows.map((row) => {
                 const advantage = row.key === 'zstd' || !zstdStored
                   ? null
                   : ((1 - (row.stored / zstdStored)) * 100);
                 const isHighlight = ['corpus_dedup', 'adaptive'].includes(row.key);
                 return (
                   <tr
                     key={row.key}
                     style={isHighlight
                       ? { background: 'var(--md-sys-color-primary-container)', fontWeight: 'bold' }
                       : { borderBottom: '1px solid var(--md-sys-color-outline-variant)' }}
                   >
                     <td style={{ padding: '1rem 2rem', color: isHighlight ? 'var(--md-sys-color-on-primary-container)' : 'inherit' }}>{row.name}</td>
                     <td style={{ padding: '1rem 2rem', fontFamily: 'monospace', color: isHighlight ? 'var(--md-sys-color-on-primary-container)' : 'inherit' }}>
                       {row.stored.toLocaleString()} B
                     </td>
                     <td style={{ padding: '1rem 2rem', color: isHighlight ? 'var(--md-sys-color-on-primary-container)' : 'inherit' }}>
                       {row.error ? '—' : `${row.ratio.toFixed(2)}×`}
                     </td>
                     <td style={{ padding: '1rem 2rem', color: isHighlight ? 'var(--md-sys-color-on-primary-container)' : 'inherit' }}>
                       {row.error ? '—' : `${row.savings.toFixed(1)}%`}
                     </td>
                     <td style={{ padding: '1rem 2rem', color: row.error ? 'var(--md-sys-color-error)' : (advantage !== null && advantage >= 0 ? 'var(--md-sys-color-primary)' : 'var(--md-sys-color-error)') }}>
                       {row.error
                         ? 'error'
                         : (advantage === null ? '—' : `${advantage >= 0 ? '+' : ''}${advantage.toFixed(1)}%`)}
                       {row.isDictionaryResult && row.savings < 0 && (
                         <span style={{ display: 'block', fontSize: '0.8rem', color: 'var(--md-sys-color-outline)' }}>
                           negative means dict overhead exceeds gain
                         </span>
                       )}
                       {row.key === 'adaptive' && row.selectedStrategyLabel && (
                         <span style={{ display: 'block', fontSize: '0.8rem', color: isHighlight ? 'var(--md-sys-color-on-primary-container)' : 'var(--md-sys-color-secondary)' }}>
                           selected: {row.selectedStrategyLabel}
                         </span>
                       )}
                     </td>
                   </tr>
                 );
               })}
             </tbody>
          </table>
        </div>
      </div>

      <div className="material-card" style={{ marginBottom: '3rem' }}>
        <h2 className="headline-large" style={{ marginBottom: '1rem' }}>Baseline Coverage in Current Evaluation</h2>
        <p className="body-large" style={{ color: 'var(--md-sys-color-secondary)', marginBottom: '1rem' }}>
          Current runs include level/quality sweeps and alternative cascades on both synthetic and real prompt corpora.
        </p>
        <ul style={{ margin: 0, paddingLeft: '1.25rem', lineHeight: 1.9 }}>
          <li><b>Brotli sweep:</b> Q1, Q5, Q9, Q11</li>
          <li><b>gzip/DEFLATE sweep:</b> L1, L6, L9</li>
          <li><b>Hybrid cascades:</b> Brotli→Zstd, Zstd→LZ4HC variants</li>
          <li><b>Core methods:</b> Per-prompt Zstd, Hybrid BPE+Zstd, Zstd dictionary, Corpus Dedup, Delta, Adaptive Router</li>
        </ul>

        {(sweeps.gzip_sweep?.best || sweeps.brotli_sweep?.best || sweeps.cascade_sweep?.best) && (
          <div style={{ marginTop: '1rem', padding: '0.75rem', borderRadius: '8px', background: 'var(--md-sys-color-surface-container-highest)' }}>
            <p style={{ margin: 0 }}>
              <b>Sweep highlights:</b>{' '}
              {sweeps.gzip_sweep?.best ? `gzip L${sweeps.gzip_sweep.best.level} (${Number(sweeps.gzip_sweep.best.ratio ?? 0).toFixed(2)}×), ` : ''}
              {sweeps.brotli_sweep?.best ? `Brotli Q${sweeps.brotli_sweep.best.quality} (${Number(sweeps.brotli_sweep.best.ratio ?? 0).toFixed(2)}×), ` : ''}
              {sweeps.cascade_sweep?.best ? `${String(sweeps.cascade_sweep.best.method || '').replace('cascade_', '')} (${Number(sweeps.cascade_sweep.best.ratio ?? 0).toFixed(2)}×)` : ''}
            </p>
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem' }}>
         <div className="material-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', alignItems: 'center', textAlign: 'center' }}>
            <div style={{ padding: '1rem', background: 'var(--md-sys-color-tertiary-container)', color: 'var(--md-sys-color-on-tertiary-container)', borderRadius: 'var(--md-sys-shape-corner-full)' }}>
              <TrendingUp size={32} />
            </div>
            <h3 className="headline-large">{bestOverall ? `${bestOverall.ratio.toFixed(2)}×` : '—'}</h3>
            <p className="label-large" style={{ color: 'var(--md-sys-color-tertiary)' }}>Dedup vs Zstd</p>
            <p className="body-large">Best overall method ratio for the selected experiment.</p>
         </div>

         <div className="material-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', alignItems: 'center', textAlign: 'center' }}>
            <div style={{ padding: '1rem', background: 'var(--md-sys-color-secondary-container)', color: 'var(--md-sys-color-on-secondary-container)', borderRadius: 'var(--md-sys-shape-corner-full)' }}>
              <Target size={32} />
            </div>
            <h3 className="headline-large">{dedupRow?.raw?.unique_nodes ?? '—'}</h3>
            <p className="label-large" style={{ color: 'var(--md-sys-color-secondary)' }}>Unique Components</p>
            <p className="body-large">Unique deduplicated content nodes in the selected experiment.</p>
         </div>

         <div className="material-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', alignItems: 'center', textAlign: 'center' }}>
            <div style={{ padding: '1rem', background: 'var(--md-sys-color-primary-container)', color: 'var(--md-sys-color-on-primary-container)', borderRadius: 'var(--md-sys-shape-corner-full)' }}>
              <FilePieChart size={32} />
            </div>
            <h3 className="headline-large">{bestBaseline ? `${bestBaseline.ratio.toFixed(2)}×` : '—'}</h3>
            <p className="label-large" style={{ color: 'var(--md-sys-color-primary)' }}>Best Baseline Settings</p>
            <p className="body-large">Top per-prompt baseline ratio for the selected experiment.</p>
         </div>
      </div>
    </div>
  );
}
