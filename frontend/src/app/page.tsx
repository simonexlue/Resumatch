export default function Home() {
  return (
    <main className="min-h-screen bg-background text-foreground p-8">
      <div className="max-w-3xl mx-auto space-y-6">
        <h1 className="text-3xl font-semibold">Resumatch</h1>
        <p className="text-muted-foreground">Paste a job description, upload a resume, get an ATS-safe tailored version.</p>
        <div className="grid gap-4">
          <a href="/demo">Open Demo</a>
        </div>
      </div>
    </main>
  )
}