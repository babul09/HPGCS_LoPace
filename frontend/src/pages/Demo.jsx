import React, { useState } from 'react';
import { PlayCircle, ShieldCheck, AlertCircle, Database, Settings2 } from 'lucide-react';

export default function Demo() {
  const [mode, setMode] = useState('synthetic'); // 'synthetic' or 'real'
  const [dictOverheadMode, setDictOverheadMode] = useState('with');
  const [compressing, setCompressing] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  // Form State
  const [nPrompts, setNPrompts] = useState(1000);
  const [systemReuse, setSystemReuse] = useState(0.8);
  const [includeTools, setIncludeTools] = useState(0.4);
  const [includeContext, setIncludeContext] = useState(0.3);
  
  const [realDataPath, setRealDataPath] = useState('/path/to/dataset.json');
  const [jsonField, setJsonField] = useState('');

  const runBenchmark = async () => {
    setCompressing(true);
    setError(null);
    setResults(null);
    
    try {
      const payload = {
        mode,
        n_prompts: Number(nPrompts),
        system_reuse: Number(systemReuse),
        include_tools: Number(includeTools),
        include_context: Number(includeContext),
        real_data_path: realDataPath,
        json_field: jsonField
      };

      const response = await fetch('/api/benchmark', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || `API error: ${response.statusText}`);
      }
      
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setCompressing(false);
    }
  };

  const getMethodAlias = (key) => {
    switch(key) {
      case 'zstd': return 'Per-prompt Zstd';
      case 'gzip': return 'Per-prompt Gzip';
      case 'brotli': return 'Per-prompt Brotli';
      case 'cascade': return 'Hybrid Cascade';
      case 'hybrid': return 'Per-prompt Hybrid';
      case 'zstd_dict': return `Zstd + Dictionary (${dictOverheadMode === 'with' ? 'with' : 'without'} overhead)`;
      case 'zstd_dictionary': return `Zstd + Dictionary (${dictOverheadMode === 'with' ? 'with' : 'without'} overhead)`;
      case 'corpus_dedup': return 'Corpus Dedup';
      case 'corpus_dedup_chunked': return 'Chunked Dedup';
      case 'delta': return 'Delta Compression';
      case 'adaptive': return 'Adaptive Router';
      default: return key;
    }
  };

  const renderSweepRows = (runs, levelKey, ratioLabel) => {
    if (!Array.isArray(runs) || runs.length === 0) return null;

    return runs.map((entry, idx) => (
      <tr key={idx} style={{ borderBottom: '1px solid var(--md-sys-color-outline-variant)' }}>
        <td style={{ padding: '0.6rem 0.75rem' }}>{entry[levelKey] ?? '-'}</td>
        <td style={{ padding: '0.6rem 0.75rem' }}>{Number(entry.ratio ?? 0).toFixed(2)}x</td>
        <td style={{ padding: '0.6rem 0.75rem' }}>{Number(entry.savings_pct ?? 0).toFixed(2)}%</td>
        <td style={{ padding: '0.6rem 0.75rem' }}>{Number(entry.time_s ?? 0).toFixed(2)}s</td>
        <td style={{ padding: '0.6rem 0.75rem', color: 'var(--md-sys-color-secondary)' }}>{ratioLabel(entry)}</td>
      </tr>
    ));
  };

  return (
    <div className="demo-container" style={{ animation: 'fadeIn 0.5s ease', display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
      
      {/* Configuration Pane */}
      <div style={{ flex: '1 1 400px', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
        <div style={{ textAlign: 'left', marginBottom: '1rem' }}>
          <h1 className="display-large" style={{ color: 'var(--md-sys-color-primary)' }}>Corpus Evaluator</h1>
          <p className="headline-large" style={{ color: 'var(--md-sys-color-secondary)' }}>Dynamically run all comprehensive benchmarks natively.</p>
        </div>

        <div className="material-card" style={{ padding: '2rem', background: 'var(--md-sys-color-surface-container-high)', borderRadius: 'var(--md-sys-shape-corner-large)' }}>
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
            <button 
              className={`material-button-primary ${mode === 'synthetic' ? '' : 'inactive'}`} 
              style={{ flex: 1, background: mode === 'synthetic' ? 'var(--md-sys-color-primary)' : 'var(--md-sys-color-surface-container-highest)', color: mode === 'synthetic' ? 'var(--md-sys-color-on-primary)' : 'var(--md-sys-color-on-surface)' }}
              onClick={() => setMode('synthetic')}
            >
              <Settings2 size={18} style={{marginRight: '0.5rem'}}/> Synthetic Engine
            </button>
            <button 
              className={`material-button-primary ${mode === 'real' ? '' : 'inactive'}`} 
              style={{ flex: 1, background: mode === 'real' ? 'var(--md-sys-color-primary)' : 'var(--md-sys-color-surface-container-highest)', color: mode === 'real' ? 'var(--md-sys-color-on-primary)' : 'var(--md-sys-color-on-surface)' }}
              onClick={() => setMode('real')}
            >
              <Database size={18} style={{marginRight: '0.5rem'}}/> Real Host File
            </button>
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label className="label-large" style={{ display: 'block', marginBottom: '0.5rem' }}>Dictionary metric view</label>
            <select
              value={dictOverheadMode}
              onChange={(e) => setDictOverheadMode(e.target.value)}
              style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--md-sys-color-outline-variant)', background: 'var(--md-sys-color-surface)', color: 'var(--md-sys-color-on-surface)' }}
            >
              <option value="with">With overhead (deployment realistic)</option>
              <option value="without">Without overhead (raw compression only)</option>
            </select>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {mode === 'real' && (
               <>
                 <div>
                    <label className="label-large" style={{display: 'block', marginBottom: '0.5rem'}}>Absolute JSON File Path</label>
                    <input 
                      type="text" 
                      value={realDataPath} 
                      onChange={(e) => setRealDataPath(e.target.value)} 
                      style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--md-sys-color-outline-variant)', background: 'var(--md-sys-color-surface)', color: 'var(--md-sys-color-on-surface)'}}
                    />
                 </div>
                 <div>
                    <label className="label-large" style={{display: 'block', marginBottom: '0.5rem'}}>JSON Field (optional auto-detect)</label>
                    <input 
                      type="text" 
                      value={jsonField} 
                      onChange={(e) => setJsonField(e.target.value)} 
                      placeholder="e.g. prompt, conversations, text"
                      style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--md-sys-color-outline-variant)', background: 'var(--md-sys-color-surface)', color: 'var(--md-sys-color-on-surface)'}}
                    />
                 </div>
                 <div>
                    <label className="label-large" style={{display: 'block', marginBottom: '0.5rem'}}>Restrict Prompt Sample Size (0 means all)</label>
                    <input 
                      type="number" 
                      value={nPrompts} 
                      onChange={(e) => setNPrompts(e.target.value)} 
                      style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--md-sys-color-outline-variant)', background: 'var(--md-sys-color-surface)', color: 'var(--md-sys-color-on-surface)'}}
                    />
                 </div>
               </>
            )}

            {mode === 'synthetic' && (
              <>
                 <div>
                    <label className="label-large" style={{display: 'block', marginBottom: '0.5rem'}}>Sample Size (Prompts): {nPrompts}</label>
                    <input 
                      type="range" min="10" max="10000" step="10" 
                      value={nPrompts} onChange={(e) => setNPrompts(e.target.value)} 
                      style={{ width: '100%' }}
                    />
                 </div>
                 <div>
                    <label className="label-large" style={{display: 'block', marginBottom: '0.5rem'}}>System Reuse Propensity: {(systemReuse * 100).toFixed(0)}%</label>
                    <input 
                      type="range" min="0" max="1" step="0.05" 
                      value={systemReuse} onChange={(e) => setSystemReuse(e.target.value)} 
                      style={{ width: '100%' }}
                    />
                 </div>
                 <div>
                    <label className="label-large" style={{display: 'block', marginBottom: '0.5rem'}}>Tool Inclusion Density: {(includeTools * 100).toFixed(0)}%</label>
                    <input 
                      type="range" min="0" max="1" step="0.05" 
                      value={includeTools} onChange={(e) => setIncludeTools(e.target.value)} 
                      style={{ width: '100%' }}
                    />
                 </div>
                 <div>
                    <label className="label-large" style={{display: 'block', marginBottom: '0.5rem'}}>Context Density: {(includeContext * 100).toFixed(0)}%</label>
                    <input 
                      type="range" min="0" max="1" step="0.05" 
                      value={includeContext} onChange={(e) => setIncludeContext(e.target.value)} 
                      style={{ width: '100%' }}
                    />
                 </div>
              </>
            )}
          </div>
        </div>

        <button 
          className="material-button-primary" 
          style={{ width: '100%', justifyContent: 'center', padding: '1.5rem', fontSize: '1.25rem', opacity: compressing ? 0.7 : 1 }}
          onClick={runBenchmark}
          disabled={compressing}
        >
          {compressing ? 'Executing Python Benchmarks...' : <><PlayCircle size={28} /> Execute Comprehensive Baseline</>}
        </button>
      </div>

      {/* Results Pane */}
      <div style={{ flex: '1 1 500px', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
         <div className="material-card" style={{ flex: 1, minHeight: '500px', display: 'flex', flexDirection: 'column' }}>
            <h2 className="headline-large" style={{ marginBottom: '1.5rem' }}>Evaluation Outcomes</h2>
            
            {!results && !compressing && !error && (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--md-sys-color-outline)' }}>
                <p>Awaiting corpus parameter configuration to initiate trial...</p>
              </div>
            )}

            {compressing && (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--md-sys-color-primary)', textAlign: 'center' }}>
                 <p className="headline-large" style={{ animation: 'pulse 1s infinite' }}>
                    Computing methodologies against standard limits...<br/><span style={{fontSize: '1rem', color: 'var(--md-sys-color-tertiary)'}}>This may take upwards of a minimum minute to resolve completely depending on host compute.</span>
                 </p>
              </div>
            )}

            {error && (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--md-sys-color-error)', flexDirection: 'column', textAlign: 'center' }}>
                 <p className="headline-large" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}><AlertCircle /> Benchmark Pipeline Failure</p>
                 <p style={{marginTop: '0.5rem'}}>{error}</p>
              </div>
            )}

            {results && !compressing && (
              <div style={{ animation: 'fadeIn 0.4s ease' }}>
                <div style={{ background: 'var(--md-sys-color-primary-container)', color: 'var(--md-sys-color-on-primary-container)', padding: '1rem', borderRadius: '8px', marginBottom: '2rem' }}>
                  <p className="label-large">Dataset Parameters Extracted:</p>
                  <p><strong>N Points:</strong> {results.metadata.n_prompts}</p>
                  <p><strong>Mean Length:</strong> {Math.round(results.metadata.mean_prompt_chars)} / char</p>
                  {results.metadata.dataset_type === 'synthetic' ? (
                     <p><strong>Actual System Reuse:</strong> {(results.metadata.actual_system_reuse_pct).toFixed(1)}%</p>
                  ) : (
                     <p><strong>Duplicate Pct:</strong> {(results.metadata.exact_duplicate_pct).toFixed(1)}%</p>
                  )}
                </div>
                 
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
                    {Object.entries(results.methods)
                      .filter(([key]) => !key.endsWith('_sweep'))
                      .map(([key, res]) => {
                      const selectedStrategy = res.selected_strategy;
                      const isDictionaryResult = key === 'zstd_dict'
                        || key === 'zstd_dictionary'
                        || (key === 'adaptive' && ['zstd_dict', 'zstd_dictionary'].includes(selectedStrategy));

                      const totalOriginal = Number(res.total_original ?? 0);
                      const totalCompressed = Number(res.total_compressed ?? 0);
                      const totalWithOverhead = Number(res.total_with_dict_overhead ?? totalCompressed);
                      const displayStored = isDictionaryResult
                        ? (dictOverheadMode === 'with' ? totalWithOverhead : totalCompressed)
                        : Number(res.total_compressed ?? res.total_with_dict_overhead ?? 0);
                      const displayRatio = isDictionaryResult
                        ? Number(
                          dictOverheadMode === 'with'
                            ? (res.ratio_with_dict ?? (displayStored ? totalOriginal / displayStored : 0))
                            : (res.ratio_without_dict ?? (displayStored ? totalOriginal / displayStored : 0))
                        )
                        : Number(res.ratio ?? res.ratio_with_dict ?? 0);
                      const displaySavings = isDictionaryResult
                        ? Number(totalOriginal ? (1 - displayStored / totalOriginal) * 100 : 0)
                        : Number(res.savings_pct ?? 0);

                      return (<div key={key} style={{ 
                         background: ['corpus_dedup', 'corpus_dedup_chunked', 'adaptive'].includes(key) ? 'var(--md-sys-color-surface-container-highest)' : 'var(--md-sys-color-surface-container)', 
                         border: ['corpus_dedup', 'corpus_dedup_chunked', 'adaptive'].includes(key) ? '2px solid var(--md-sys-color-primary)' : '1px solid var(--md-sys-color-outline-variant)',
                         padding: '1.5rem', borderRadius: 'var(--md-sys-shape-corner-medium)' 
                      }}>
                        <p className="label-large" style={{ color: 'var(--md-sys-color-primary)', display: 'flex', justifyContent: 'space-between' }}>
                           {getMethodAlias(key)} 
                           {['corpus_dedup', 'corpus_dedup_chunked', 'adaptive'].includes(key) && <ShieldCheck size={18} color="var(--md-sys-color-tertiary)"/>}
                        </p>
                        
                        {res.error ? (
                          <p style={{ color: 'var(--md-sys-color-error)', marginTop: '1rem' }}>{res.error}</p>
                        ) : (
                          <>
                            <h3 style={{ margin: '1rem 0', fontSize: '2rem', color: 'var(--md-sys-color-on-surface)' }}>
                             {displayRatio.toFixed(2)}x
                            </h3>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', fontSize: '0.85rem', color: 'var(--md-sys-color-on-surface-variant)'}}>
                             <p><strong>Savings:</strong> {displaySavings.toFixed(2)}%</p>
                             <p><strong>Stored Bytes:</strong> {displayStored.toLocaleString()}</p>
                             <p><strong>Time:</strong> {Number(res.time_s ?? 0).toFixed(2)} s</p>
                               {res.dictionary_size && <p><strong>Dict:</strong> {res.dictionary_size} b</p>}
                               {res.ratio_without_dict && <p><strong>Ratio (no overhead):</strong> {Number(res.ratio_without_dict).toFixed(2)}x</p>}
                               {res.ratio_with_dict && <p><strong>Ratio (with overhead):</strong> {Number(res.ratio_with_dict).toFixed(2)}x</p>}
                               {(isDictionaryResult && displaySavings < 0) && (
                                 <p style={{ color: 'var(--md-sys-color-outline)' }}><strong>Note:</strong> Negative savings here means dictionary overhead is larger than compression gain for this run.</p>
                               )}
                               {res.unique_nodes && <p><strong>Nodes:</strong> {res.unique_nodes}</p>}
                               {res.n_deltas && <p><strong>Deltas:</strong> {res.n_deltas}</p>}
                               {key === 'adaptive' && res.selected_strategy && (
                                   <div style={{ marginTop: '0.75rem', padding: '0.5rem', background: 'var(--md-sys-color-primary-container)', color: 'var(--md-sys-color-on-primary-container)', borderRadius: '4px' }}>
                                     <strong>Optimal Strategy:</strong> {getMethodAlias(res.selected_strategy)}
                                   </div>
                               )}
                            </div>
                          </>
                        )}
                      </div>
                    )})}
                 </div>

                 {(results.methods.gzip_sweep || results.methods.brotli_sweep || results.methods.cascade_sweep) && (
                   <div className="material-card" style={{ marginTop: '0.5rem', background: 'var(--md-sys-color-surface-container-high)', padding: '1rem' }}>
                     <h3 className="headline-large" style={{ marginBottom: '1rem' }}>Sweep Details</h3>

                     {results.methods.gzip_sweep?.runs?.length > 0 && (
                       <div style={{ marginBottom: '1.25rem' }}>
                         <p className="label-large" style={{ marginBottom: '0.5rem' }}>Gzip/DEFLATE Levels</p>
                         <div style={{ overflowX: 'auto' }}>
                           <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                             <thead>
                               <tr style={{ background: 'var(--md-sys-color-surface-container-highest)' }}>
                                 <th style={{ textAlign: 'left', padding: '0.6rem 0.75rem' }}>Level</th>
                                 <th style={{ textAlign: 'left', padding: '0.6rem 0.75rem' }}>Ratio</th>
                                 <th style={{ textAlign: 'left', padding: '0.6rem 0.75rem' }}>Savings</th>
                                 <th style={{ textAlign: 'left', padding: '0.6rem 0.75rem' }}>Time</th>
                                 <th style={{ textAlign: 'left', padding: '0.6rem 0.75rem' }}>Note</th>
                               </tr>
                             </thead>
                             <tbody>
                               {renderSweepRows(results.methods.gzip_sweep.runs, 'level', (entry) =>
                                 entry.level === results.methods.gzip_sweep?.best?.level ? 'best' : ''
                               )}
                             </tbody>
                           </table>
                         </div>
                       </div>
                     )}

                     {results.methods.brotli_sweep?.runs?.length > 0 && (
                       <div style={{ marginBottom: '1.25rem' }}>
                         <p className="label-large" style={{ marginBottom: '0.5rem' }}>Brotli Qualities</p>
                         <div style={{ overflowX: 'auto' }}>
                           <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                             <thead>
                               <tr style={{ background: 'var(--md-sys-color-surface-container-highest)' }}>
                                 <th style={{ textAlign: 'left', padding: '0.6rem 0.75rem' }}>Quality</th>
                                 <th style={{ textAlign: 'left', padding: '0.6rem 0.75rem' }}>Ratio</th>
                                 <th style={{ textAlign: 'left', padding: '0.6rem 0.75rem' }}>Savings</th>
                                 <th style={{ textAlign: 'left', padding: '0.6rem 0.75rem' }}>Time</th>
                                 <th style={{ textAlign: 'left', padding: '0.6rem 0.75rem' }}>Note</th>
                               </tr>
                             </thead>
                             <tbody>
                               {renderSweepRows(results.methods.brotli_sweep.runs, 'quality', (entry) =>
                                 entry.quality === results.methods.brotli_sweep?.best?.quality ? 'best' : ''
                               )}
                             </tbody>
                           </table>
                         </div>
                       </div>
                     )}

                     {results.methods.cascade_sweep?.runs?.length > 0 && (
                       <div>
                         <p className="label-large" style={{ marginBottom: '0.5rem' }}>Hybrid Cascades</p>
                         <div style={{ overflowX: 'auto' }}>
                           <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                             <thead>
                               <tr style={{ background: 'var(--md-sys-color-surface-container-highest)' }}>
                                 <th style={{ textAlign: 'left', padding: '0.6rem 0.75rem' }}>Cascade</th>
                                 <th style={{ textAlign: 'left', padding: '0.6rem 0.75rem' }}>Ratio</th>
                                 <th style={{ textAlign: 'left', padding: '0.6rem 0.75rem' }}>Savings</th>
                                 <th style={{ textAlign: 'left', padding: '0.6rem 0.75rem' }}>Time</th>
                                 <th style={{ textAlign: 'left', padding: '0.6rem 0.75rem' }}>Status</th>
                               </tr>
                             </thead>
                             <tbody>
                               {results.methods.cascade_sweep.runs.map((entry, idx) => (
                                 <tr key={idx} style={{ borderBottom: '1px solid var(--md-sys-color-outline-variant)' }}>
                                   <td style={{ padding: '0.6rem 0.75rem' }}>{String(entry.method || '').replace('cascade_', '')}</td>
                                   <td style={{ padding: '0.6rem 0.75rem' }}>{Number(entry.ratio ?? 0).toFixed(2)}x</td>
                                   <td style={{ padding: '0.6rem 0.75rem' }}>{Number(entry.savings_pct ?? 0).toFixed(2)}%</td>
                                   <td style={{ padding: '0.6rem 0.75rem' }}>{Number(entry.time_s ?? 0).toFixed(2)}s</td>
                                   <td style={{ padding: '0.6rem 0.75rem', color: entry.error ? 'var(--md-sys-color-error)' : 'var(--md-sys-color-secondary)' }}>
                                     {entry.error ? 'unavailable' : (entry.method === results.methods.cascade_sweep?.best?.method ? 'best' : 'ok')}
                                   </td>
                                 </tr>
                               ))}
                             </tbody>
                           </table>
                         </div>
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
}
