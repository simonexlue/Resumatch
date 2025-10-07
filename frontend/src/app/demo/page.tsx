'use client';
import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';

type Requirement = { skill: string; priority: 'must' | 'nice' };
type ParsedJD = {
  title?: string | null;
  company?: string | null;
  seniority?: string | null;
  requirements: Requirement[];
  responsibilities: string[];
};

// === Phase 3 shapes ===
type Bullet = { id: string; text: string; skills: string[] };

type ExperienceEntry = {
  company?: string | null;
  title?: string | null;
  start?: string | null; // "YYYY-MM" or "PRESENT"
  end?: string | null;   // "YYYY-MM" or "PRESENT"
  stack: string[];
  bullets: Bullet[];
};

type ProjectEntry = {
  name?: string | null;
  stack: string[];
  bullets: Bullet[];
};

type ResumeOut = {
  basics: { name?: string | null; email?: string | null; links: string[] };
  experience: ExperienceEntry[];
  projects: ProjectEntry[];
  skills: string[];     // top-level parsed skills pool (not the per-entry stack)
  education: string[];
};

export default function Demo() {
  // Job Description states
  const [jd, setJd] = useState('');
  const [loadingJD, setLoadingJD] = useState(false);
  const [parsed, setParsed] = useState<ParsedJD | null>(null);

  // Resume states
  const [resume, setResume] = useState<ResumeOut | null>(null);
  const [loadingCV, setLoadingCV] = useState(false);
  const [file, setFile] = useState<File | null>(null);

  const [error, setError] = useState<string | null>(null);

  const analyze = async () => {
    setLoadingJD(true);
    setError(null);
    setParsed(null);
    try {
      const res = await fetch('http://localhost:8000/parse-jd', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ raw_text: jd })
      });
      if (!res.ok) throw new Error(`Error: ${res.status}`);
      const data: ParsedJD = await res.json();
      setParsed(data);
    } catch (e: any) {
      setError(e.message || 'Failed to analyze');
    } finally {
      setLoadingJD(false);
    }
  };

  const ingestResume = async () => {
    if (!file) return;
    setLoadingCV(true);
    setError(null);
    setResume(null);
    try {
      const form = new FormData();
      form.append('file', file);
      const res = await fetch('http://localhost:8000/resume/ingest', {
        method: 'POST',
        body: form
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: ResumeOut = await res.json();
      setResume(data);
    } catch (e: any) {
      setError(e.message || 'Failed to ingest resume');
    } finally {
      setLoadingCV(false);
    }
  };

  // --- helpers ---
  const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  function fmtDate(ym?: string | null) {
    if (!ym) return '—';
    if (ym === 'PRESENT') return 'Present';
    // expect "YYYY-MM"
    const [y, m] = ym.split('-');
    const idx = Math.max(0, Math.min(11, Number(m) - 1));
    return `${monthNames[idx]} ${y}`;
  }

  function DateRange({ start, end }: { start?: string | null; end?: string | null }) {
    if (!start && !end) return <span className="opacity-70">—</span>;
    return <span className="opacity-70">{fmtDate(start)} {end ? `– ${fmtDate(end)}` : ''}</span>;
  }

  function StackBadges({ items }: { items: string[] }) {
    if (!items?.length) return null;
    return (
      <div className="flex flex-wrap gap-1.5 mt-2">
        {items.map((s, i) => (
          <Badge key={`${s}-${i}`} variant="secondary">{s}</Badge>
        ))}
      </div>
    );
  }

  return (
    <main className="min-h-screen p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <h2 className="text-2xl font-semibold">Analyze Job Description</h2>
        <Card className="p-4 space-y-2">
          <label className="text-sm font-medium">Job Description</label>
          <Textarea
            value={jd}
            onChange={e => setJd(e.target.value)}
            rows={10}
            placeholder="Paste job description..."
          />
          <div className="flex gap-2">
            <Button onClick={analyze} disabled={!jd.trim() || loadingJD}>
              {loadingJD ? 'Analyzing...' : 'Analyze'}
            </Button>
            <Button
              variant="secondary"
              onClick={() => { setParsed(null); setJd(''); }}
            >
              Clear
            </Button>
          </div>
        </Card>

        <h2 className="text-2xl font-semibold">Upload Resume</h2>
        <Card className="p-4 space-y-2">
          <input
            type="file"
            accept=".pdf,.docx"
            onChange={e => setFile(e.target.files?.[0] || null)}
          />
          <div className="flex gap-2">
            <Button onClick={ingestResume} disabled={!file || loadingCV}>
              {loadingCV ? 'Uploading…' : 'Ingest Resume'}
            </Button>
          </div>
        </Card>

        {error && (
          <Card className="p-4">
            <p className="text-red-600 font-medium">Error: {error}</p>
          </Card>
        )}

        {/* Parsed JD result */}
        {parsed && (
          <Card className="p-4 space-y-3">
            <h3 className="text-lg font-semibold">Parsed JD</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
              <div><span className="font-medium">Title:</span> {parsed.title || '—'}</div>
              <div><span className="font-medium">Company:</span> {parsed.company || '—'}</div>
              <div><span className="font-medium">Seniority:</span> {parsed.seniority || '—'}</div>
            </div>
            <div className="mt-2">
              <p className="font-medium text-sm">Requirements</p>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {parsed.requirements?.length
                  ? parsed.requirements.map((r, i) => (
                      <Badge key={i} variant={r.priority === 'must' ? 'default' : 'secondary'}>
                        {r.skill} {r.priority === 'must' ? '• must' : '• nice'}
                      </Badge>
                    ))
                  : <span className="text-sm opacity-70">—</span>
                }
              </div>
            </div>
            {parsed.responsibilities?.length ? (
              <div className="mt-2">
                <p className="font-medium text-sm">Responsibilities</p>
                <ul className="list-disc ml-6 text-sm">
                  {parsed.responsibilities.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              </div>
            ) : null}
            <pre className="mt-3 text-xs bg-muted p-2 rounded overflow-auto">
              {JSON.stringify(parsed, null, 2)}
            </pre>
          </Card>
        )}

        {/* Parsed Resume result */}
        {resume && (
          <Card className="p-4 space-y-3">
            <h3 className="text-lg font-semibold">Parsed Resume</h3>

            <div className="text-sm space-y-1">
              <p><strong>Name:</strong> {resume.basics.name || '—'}</p>
              <p><strong>Email:</strong> {resume.basics.email || '—'}</p>
              {resume.basics.links?.length ? (
                <p><strong>Links:</strong> {resume.basics.links.join(' · ')}</p>
              ) : null}
              <p><strong>Skills (top-level pool):</strong> {resume.skills.join(', ') || '—'}</p>
            </div>

            {/* Experience entries */}
            {resume.experience?.length ? (
              <div className="mt-3 space-y-3">
                <p className="font-medium">Experience</p>
                {resume.experience.map((e, idx) => (
                  <div key={idx} className="rounded-lg border p-4">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                      <div className="font-semibold">
                        {e.title ? `${e.title} — ` : ''}{e.company || '—'}
                      </div>
                      <div className="text-sm"><DateRange start={e.start} end={e.end} /></div>
                    </div>
                    <StackBadges items={e.stack} />
                    {e.bullets?.length ? (
                      <ul className="list-disc ml-6 mt-2 space-y-1 text-sm">
                        {e.bullets.map(b => (
                          <li key={b.id}>
                            {b.text}
                            {b.skills?.length ? (
                              <span className="ml-2 text-xs opacity-80">
                                [{b.skills.join(', ')}]
                              </span>
                            ) : null}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : null}

            {/* Project entries */}
            {resume.projects?.length ? (
              <div className="mt-4 space-y-3">
                <p className="font-medium">Projects</p>
                {resume.projects.map((p, idx) => (
                  <div key={idx} className="rounded-lg border p-4">
                    <div className="font-semibold">{p.name || '—'}</div>
                    <StackBadges items={p.stack} />
                    {p.bullets?.length ? (
                      <ul className="list-disc ml-6 mt-2 space-y-1 text-sm">
                        {p.bullets.map(b => (
                          <li key={b.id}>
                            {b.text}
                            {b.skills?.length ? (
                              <span className="ml-2 text-xs opacity-80">
                                [{b.skills.join(', ')}]
                              </span>
                            ) : null}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : null}

            {/* Education */}
            {resume.education?.length ? (
              <div className="mt-4">
                <p className="font-medium">Education</p>
                <ul className="list-disc ml-6 text-sm">
                  {resume.education.map((e, i) => <li key={i}>{e}</li>)}
                </ul>
            </div>
            ) : null}

            <pre className="mt-4 text-xs bg-muted p-2 rounded overflow-auto">
              {JSON.stringify(resume, null, 2)}
            </pre>
          </Card>
        )}
      </div>
    </main>
  );
}
