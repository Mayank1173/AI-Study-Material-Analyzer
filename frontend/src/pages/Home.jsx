import React from 'react'
import { Link } from 'react-router-dom'
import AppLayout from '../components/AppLayout'

function Home() {
  return (
    <AppLayout>
      <div className="space-y-8">
        <section className="rounded-3xl bg-gradient-to-r from-blue-700 to-indigo-900 p-10 text-white md:p-14">
          <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-blue-200">
            AI-Powered Learning Assistant
          </p>

          <h1 className="max-w-3xl text-4xl font-bold leading-tight md:text-6xl">
            Turn Your Study Materials Into Smart Learning
          </h1>

          <p className="mt-5 max-w-2xl text-lg leading-8 text-blue-100">
            Upload your notes, PDFs, PPTs, handwritten materials, question
            banks, previous-year papers, and educational videos. StudyAI
            organizes everything and helps you learn better.
          </p>

          <div className="mt-8 flex flex-wrap gap-4">
            <Link
              to="/dashboard"
              className="rounded-xl bg-white px-6 py-3 font-semibold text-blue-700 hover:bg-blue-50"
            >
              Explore Dashboard
            </Link>

            <Link
              to="/upload"
              className="rounded-xl border border-blue-300 px-6 py-3 font-semibold text-white hover:bg-blue-800"
            >
              Upload Materials
            </Link>
          </div>
        </section>

        <section className="grid gap-6 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-xl font-semibold text-white">
              Upload Anything
            </h2>
            <p className="mt-3 text-slate-400">
              Add PDFs, PPTs, images, handwritten notes, question papers, and
              videos.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-xl font-semibold text-white">
              Ask Questions
            </h2>
            <p className="mt-3 text-slate-400">
              Get answers based on all your uploaded study materials.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-xl font-semibold text-white">
              Learn Smarter
            </h2>
            <p className="mt-3 text-slate-400">
              Find important topics, repeated questions, summaries, and
              personalized revision insights.
            </p>
          </div>
        </section>
      </div>
    </AppLayout>
  )
}

export default Home