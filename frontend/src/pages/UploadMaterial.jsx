import { useState } from 'react'

function UploadMaterial() {
  const [files, setFiles] = useState([])
  const [uploadMessage, setUploadMessage] = useState('')

  const handleFiles = (event) => {
    const selectedFiles = Array.from(event.target.files || [])

    setFiles((currentFiles) => [...currentFiles, ...selectedFiles])
    setUploadMessage('')

    event.target.value = ''
  }

  const removeFile = (indexToRemove) => {
    setFiles((currentFiles) =>
      currentFiles.filter((_, index) => index !== indexToRemove)
    )
    setUploadMessage('')
  }

  const handleUpload = () => {
    if (files.length === 0) return

    setUploadMessage(
      `${files.length} material${files.length !== 1 ? 's' : ''} ready for AI analysis.`
    )
  }

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`

    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <nav className="flex items-center justify-between border-b border-slate-800 bg-slate-900 px-8 py-5">
        <a href="/dashboard" className="text-2xl font-bold text-blue-400">
          StudyAI
        </a>

        <div className="flex gap-6">
          <a href="/dashboard" className="text-slate-300 hover:text-white">
            Dashboard
          </a>
          <a href="/chat" className="text-slate-300 hover:text-white">
            AI Chat
          </a>
        </div>
      </nav>

      <main className="mx-auto max-w-4xl px-6 py-12">
        <div className="mb-8">
          <h2 className="text-3xl font-bold">Upload Study Materials</h2>
          <p className="mt-2 text-slate-400">
            Upload notes, PDFs, PPTs, question papers, images, and videos.
          </p>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-8">
          <label className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-700 bg-slate-950 px-6 py-16 text-center transition hover:border-blue-500">
            <div className="text-5xl">📚</div>

            <h3 className="mt-4 text-xl font-semibold">
              Select your study materials
            </h3>

            <p className="mt-2 text-slate-400">
              Choose one or multiple files from your computer.
            </p>

            <span className="mt-6 rounded-lg bg-blue-600 px-6 py-3 font-semibold hover:bg-blue-700">
              Choose Files
            </span>

            <input
              type="file"
              multiple
              accept=".pdf,.ppt,.pptx,.doc,.docx,.txt,.jpg,.jpeg,.png,.mp4,.mov,.avi"
              onChange={handleFiles}
              className="hidden"
            />
          </label>

          <div className="mt-8">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold">Selected Files</h3>

              <span className="text-sm text-slate-400">
                {files.length} file{files.length !== 1 ? 's' : ''}
              </span>
            </div>

            {files.length === 0 ? (
              <div className="rounded-lg border border-slate-800 bg-slate-950 p-6 text-center text-slate-500">
                No files selected yet.
              </div>
            ) : (
              <div className="space-y-3">
                {files.map((file, index) => (
                  <div
                    key={`${file.name}-${file.lastModified}-${index}`}
                    className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 p-4"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium">{file.name}</p>

                      <p className="mt-1 text-sm text-slate-400">
                        {file.type || 'Unknown file type'} •{' '}
                        {formatFileSize(file.size)}
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={() => removeFile(index)}
                      className="ml-4 rounded-md px-3 py-2 text-sm text-red-400 hover:bg-red-500/10 hover:text-red-300"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={handleUpload}
            disabled={files.length === 0}
            className="mt-8 w-full rounded-lg bg-blue-600 px-6 py-3 font-semibold hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Upload Materials
          </button>

          {uploadMessage && (
            <p className="mt-4 rounded-lg border border-green-500/30 bg-green-500/10 p-4 text-center text-green-400">
              {uploadMessage}
            </p>
          )}
        </div>
      </main>
    </div>
  )
}

export default UploadMaterial