import React from 'react';
import { TrendingUp, FilePieChart, Target } from 'lucide-react';

export default function Benchmarks() {
  return (
    <div className="benchmarks-container" style={{ animation: 'fadeIn 0.5s ease' }}>
      <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
        <h1 className="display-large" style={{ color: 'var(--md-sys-color-primary)' }}>Benchmark Results</h1>
        <p className="headline-large" style={{ color: 'var(--md-sys-color-secondary)' }}>Comprehensive evaluation across synthetic and real-world LLM prompt corpora</p>
      </div>

      <div className="material-card" style={{ marginBottom: '3rem', padding: '0', overflow: 'hidden' }}>
        <div style={{ padding: '2rem', background: 'var(--md-sys-color-primary-container)' }}>
          <h2 className="headline-large" style={{ color: 'var(--md-sys-color-on-primary-container)' }}>Method Comparison (1000 prompts, 80% system reuse)</h2>
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
               <tr style={{ borderBottom: '1px solid var(--md-sys-color-outline-variant)' }}>
                 <td style={{ padding: '1rem 2rem' }}>Per-prompt Zstd</td>
                 <td style={{ padding: '1rem 2rem', fontFamily: 'monospace' }}>1,153,204 B</td>
                 <td style={{ padding: '1rem 2rem' }}>1.84×</td>
                 <td style={{ padding: '1rem 2rem' }}>45.7%</td>
                 <td style={{ padding: '1rem 2rem', color: 'var(--md-sys-color-outline)' }}>—</td>
               </tr>
               <tr style={{ borderBottom: '1px solid var(--md-sys-color-outline-variant)' }}>
                 <td style={{ padding: '1rem 2rem' }}>Per-prompt Hybrid</td>
                 <td style={{ padding: '1rem 2rem', fontFamily: 'monospace' }}>1,498,716 B</td>
                 <td style={{ padding: '1rem 2rem' }}>1.42×</td>
                 <td style={{ padding: '1rem 2rem' }}>29.5%</td>
                 <td style={{ padding: '1rem 2rem', color: 'var(--md-sys-color-error)' }}>-29.9%</td>
               </tr>
               <tr style={{ borderBottom: '1px solid var(--md-sys-color-outline-variant)' }}>
                 <td style={{ padding: '1rem 2rem' }}>Zstd Dictionary</td>
                 <td style={{ padding: '1rem 2rem', fontFamily: 'monospace' }}>580,000 B</td>
                 <td style={{ padding: '1rem 2rem' }}>3.66×</td>
                 <td style={{ padding: '1rem 2rem' }}>72.7%</td>
                 <td style={{ padding: '1rem 2rem', color: 'var(--md-sys-color-primary)' }}>+49.7%</td>
               </tr>
               <tr style={{ background: 'var(--md-sys-color-primary-container)', fontWeight: 'bold' }}>
                 <td style={{ padding: '1rem 2rem', color: 'var(--md-sys-color-on-primary-container)' }}>Corpus Dedup (Proposed)</td>
                 <td style={{ padding: '1rem 2rem', fontFamily: 'monospace', color: 'var(--md-sys-color-on-primary-container)' }}>171,394 B</td>
                 <td style={{ padding: '1rem 2rem', color: 'var(--md-sys-color-on-primary-container)' }}>12.40×</td>
                 <td style={{ padding: '1rem 2rem', color: 'var(--md-sys-color-on-primary-container)' }}>91.9%</td>
                 <td style={{ padding: '1rem 2rem', color: 'var(--md-sys-color-primary)' }}>+85.1%</td>
               </tr>
             </tbody>
          </table>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem' }}>
         <div className="material-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', alignItems: 'center', textAlign: 'center' }}>
            <div style={{ padding: '1rem', background: 'var(--md-sys-color-tertiary-container)', color: 'var(--md-sys-color-on-tertiary-container)', borderRadius: 'var(--md-sys-shape-corner-full)' }}>
              <TrendingUp size={32} />
            </div>
            <h3 className="headline-large">330 B / prompt</h3>
            <p className="label-large" style={{ color: 'var(--md-sys-color-tertiary)' }}>Marginal Cost Limit</p>
            <p className="body-large">Average storage cost per additional prompt after initial corpus registry components are mapped.</p>
         </div>

         <div className="material-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', alignItems: 'center', textAlign: 'center' }}>
            <div style={{ padding: '1rem', background: 'var(--md-sys-color-secondary-container)', color: 'var(--md-sys-color-on-secondary-container)', borderRadius: 'var(--md-sys-shape-corner-full)' }}>
              <Target size={32} />
            </div>
            <h3 className="headline-large">38 Nodes</h3>
            <p className="label-large" style={{ color: 'var(--md-sys-color-secondary)' }}>Unique Extractions</p>
            <p className="body-large">Only 38 unique content components verified, compressed, and stored across 1000 production-level prompts.</p>
         </div>

         <div className="material-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', alignItems: 'center', textAlign: 'center' }}>
            <div style={{ padding: '1rem', background: 'var(--md-sys-color-primary-container)', color: 'var(--md-sys-color-on-primary-container)', borderRadius: 'var(--md-sys-shape-corner-full)' }}>
              <FilePieChart size={32} />
            </div>
            <h3 className="headline-large">61.1%</h3>
            <p className="label-large" style={{ color: 'var(--md-sys-color-primary)' }}>Blueprint Overhead</p>
            <p className="body-large">Fraction of stored database bytes dedicated specifically to lightweight SQLite reconstruction blueprints vs content payloads.</p>
         </div>
      </div>
    </div>
  );
}
