import { useState } from 'react'

function Chat() {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([
    {
      role: 'ai',
      text: 'Hello! Upload your study materials and ask me anything about your subjects.',
    },
  ])

  const handleSubmit = (event) => {
    event.preventDefault()

    if (!question.trim()) return

    setMessages((currentMessages) => [
      ...currentMessages,
      {
        role: 'user',
        text: question,
      },
      {
        role: 'ai',
        text: `I received your question: "${question}". AI-generated answers will be connected after the backend is added.`,
      },
    ])

    setQuestion('')
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-white">
      <nav className="flex items-center justify-between border-b border-slate-800 bg-slate-900 px-8 py-5">
        <a href="/dashboard" className="text-2xl font-bold text-blue-400">
          StudyAI
        </a>

        <a href="/upload" className="text-slate-300 hover:text-white">
          Upload Materials
        </a>
      </nav>

      <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col px-6 py-10">
        <h2 className="text-3xl font-bold">Ask StudyAI</h2>

        <p className="mt-2 text-slate-400">
          Ask questions based on your uploaded study materials.
        </p>

        <div className="mt-8 flex flex-1 flex-col rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <div className="flex-1 space-y-4 overflow-y-auto">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`max-w-3xl rounded-xl p-4 ${
                  message.role === 'user'
                    ? 'ml-auto bg-blue-600'
                    : 'bg-slate-800'
                }`}
              >
                <p className="text-sm text-slate-300">
                  {message.role === 'user' ? 'You' : 'AI Assistant'}
                </p>

                <p className="mt-2">{message.text}</p>
              </div>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="mt-6 flex gap-3">
            <input
              type="text"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask a question about your study material..."
              className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 outline-none focus:border-blue-500"
            />

            <button
              type="submit"
              className="rounded-lg bg-blue-600 px-6 py-3 font-semibold hover:bg-blue-700"
            >
              Send
            </button>
          </form>
        </div>
      </main>
    </div>
  )
}

export default Chat