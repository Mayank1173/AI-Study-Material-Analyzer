import Navbar from '../components/Navbar'

function Dashboard() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <Navbar />

      <main className="mx-auto max-w-6xl px-6 py-12">
        <div className="mb-10">
          <p className="text-blue-400">Welcome back</p>

          <h1 className="mt-2 text-4xl font-bold">
            Your Study Dashboard
          </h1>

          <p className="mt-3 text-slate-400">
            Manage your study materials and continue learning with AI.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          <a
            href="/upload"
            className="rounded-2xl border border-slate-800 bg-slate-900 p-6 transition hover:border-blue-500"
          >
            <div className="text-4xl">📚</div>

            <h2 className="mt-5 text-xl font-semibold">
              Upload Materials
            </h2>

            <p className="mt-2 text-slate-400">
              Add notes, PDFs, PPTs, images, and videos.
            </p>
          </a>

          <a
            href="/chat"
            className="rounded-2xl border border-slate-800 bg-slate-900 p-6 transition hover:border-blue-500"
          >
            <div className="text-4xl">💬</div>

            <h2 className="mt-5 text-xl font-semibold">
              Ask AI Questions
            </h2>

            <p className="mt-2 text-slate-400">
              Ask questions based on your uploaded study materials.
            </p>
          </a>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <div className="text-4xl">🧠</div>

            <h2 className="mt-5 text-xl font-semibold">
              Smart Insights
            </h2>

            <p className="mt-2 text-slate-400">
              Generate summaries, important topics, and exam-focused insights.
            </p>
          </div>
        </div>

        <section className="mt-10 rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="text-2xl font-bold">Recent Activity</h2>

          <p className="mt-2 text-slate-400">
            Your uploaded materials and AI-generated insights will appear here.
          </p>

          <div className="mt-6 rounded-lg border border-dashed border-slate-700 p-8 text-center text-slate-500">
            No recent materials yet. Upload your first study material to begin.
          </div>
        </section>
      </main>
    </div>
  )
}

export default Dashboard