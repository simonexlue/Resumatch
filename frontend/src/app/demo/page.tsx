'use client';
import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

type Requirement = { skill: string; priority: 'must' | 'nice' };
type ParsedJD = {
  title?: string | null;
  company?: string | null;
  seniority?: string | null;
  requirements: Requirement[];
  responsibilities: string[];
};

export default function Demo() {
  const [jd, setJd] = useState('');
  const [loading, setLoading] = useState(false);
  const [parsed, setParsed] = useState<ParsedJD | null>(null);
  const [error, setError] = useState<string | null>(null);

  const analyze = async () => {
    setLoading(true);
    setError(null);
    setParsed(null);
    try {
      const res = await fetch('http://localhost:8000/parse-jd', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ raw_text: jd})
      });
      if(!res.ok) throw new Error(`Error: ${res.status}`);
      const data = await res.json();
      setParsed(data);
    } catch (e: any) {
      setError(e.message || "Failed to analyze");
    } finally {
      setLoading(false);
    }
  };

  return (
  <main className="min-h-screen p-6">
    <div className="max-w-3xl mx-auto space-y-4">
      <h2 className="text-2xl font-semibold">Analyze Job Description</h2>
      <Card className="p-4 space-y-2">
        <label className="text-sm font-medium">Job Description</label>
        <Textarea 
          value={jd} 
          onChange={e => setJd(e.target.value)} 
          rows={10} 
          placeholder="Paste job description..." />
        <div className="flex gap-2">
          <Button 
            onClick={analyze}
            disabled={!jd.trim() || loading}>
              {loading ? 'Analyzing...' : 'Analyze'}
          </Button>
          <Button
            variant="secondary"
            onClick={() => {setParsed(null); setJd('');}}
            >
              Clear
            </Button>
        </div>
      </Card>

      {error && (
        <Card className='p-4'>
          <p className="text-red-600 font-medium">Error: {error}</p>
        </Card>
      )}

      {parsed && (
        <Card className='p-4 space-y-2'>
          <h3 className='text-lg font-semibold'>Parsed Result</h3>
          <div className='text-sm'>
            <p><strong>Title: </strong> {parsed.title || "-"}</p>
            <p><strong>Company: </strong> {parsed.company || "-"}</p>
            <p><strong>Seniority: </strong> {parsed.seniority || "-"}</p>
            <p><strong>Requirements:</strong> {parsed.title || "-"}</p>
            <ul className='list-disc ml-6'>
              {parsed.requirements.map((r, idx) => (
                <li key={idx}>{r.skill} ({r.priority})</li>
              ))}
            </ul>
            <p className='mt-2'><strong>Responsibilities:</strong></p>
            <ul className='list-disc ml-6'>
              {parsed.responsibilities.map((r, idx) => (
                <li key={idx}>{r}</li>
              ))}
            </ul>
          </div>
          <pre className='mt-4 text-xs bg-muted p-2 rounded overflow-auto'>
            {JSON.stringify(parsed, null, 2)}
          </pre>
        </Card>
      )}
    </div>
  </main>
  )
}