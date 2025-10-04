'use client';
import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

export default function Demo() {
    const [jd, setJd] = useState('');
    return (
    <main className="min-h-screen p-6">
      <div className="max-w-3xl mx-auto space-y-4">
        <h2 className="text-2xl font-semibold">Phase 2 hook (coming next)</h2>
        <Card className="p-4 space-y-2">
          <label className="text-sm font-medium">Job Description</label>
          <Textarea value={jd} onChange={e => setJd(e.target.value)} rows={8} placeholder="Paste JD..." />
          <div className="flex gap-2">
            <Button disabled>Analyze (wire to /parse-jd)</Button>
          </div>
        </Card>
      </div>
    </main>
    )
}