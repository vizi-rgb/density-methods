import { useState, useEffect, useRef } from 'react'
import { FileUpload } from './components/FileUpload'
import { JobStatus } from './components/JobStatus'
import { VideoPlayerGrid } from './components/VideoPlayerGrid'
import { uploadVideo } from './api/client'
import { openSSEStream } from './api/sseStream'
import type { AppState, VideoOutput } from './types'
import './App.css'

export default function App() {
  const [appState, setAppState] = useState<AppState>('IDLE')
  const [progress, setProgress] = useState(0)
  const [outputs, setOutputs] = useState<VideoOutput[]>([])
  const [error, setError] = useState<string | null>(null)
  const sseRef = useRef<EventSource | null>(null)

  // Cleanup SSE on unmount
  useEffect(() => {
    return () => {
      sseRef.current?.close()
    }
  }, [])

  const reset = () => {
    sseRef.current?.close()
    sseRef.current = null
    setAppState('IDLE')
    setProgress(0)
    setOutputs([])
    setError(null)
  }

  const handleUpload = async (file: File) => {
    setAppState('UPLOADING')
    setError(null)
    try {
      const { job_id } = await uploadVideo(file)
      setAppState('PROCESSING')
      setProgress(0)

      const es = openSSEStream(
        job_id,
        (event) => {
          if (event.status === 'processing') {
            setProgress(event.progress)
          } else if (event.status === 'completed') {
            es.close()
            sseRef.current = null
            setProgress(100)
            setOutputs(event.outputs ?? [])
            setAppState('READY_TO_PLAY')
          } else if (event.status === 'failed') {
            es.close()
            sseRef.current = null
            setError(event.error ?? 'Przetwarzanie nie powiodło się')
            setAppState('ERROR')
          }
        },
        () => {
          if (appState === 'PROCESSING') {
            setError('Utracono połączenie SSE')
            setAppState('ERROR')
          }
        },
      )
      sseRef.current = es
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Błąd wysyłania pliku')
      setAppState('ERROR')
    }
  }

  return (
    <main style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '2rem', gap: '2rem', minHeight: '100vh' }}>
      <h1>Analiza Wideo</h1>

      {appState === 'IDLE' && (
        <FileUpload onUpload={handleUpload} />
      )}

      {appState === 'UPLOADING' && (
        <p>⏳ Wysyłanie pliku...</p>
      )}

      {appState === 'PROCESSING' && (
        <JobStatus progress={progress} />
      )}

      {appState === 'READY_TO_PLAY' && (
        <>
          <VideoPlayerGrid outputs={outputs} />
          <button onClick={reset}>↩ Nowa analiza</button>
        </>
      )}

      {appState === 'ERROR' && (
        <div style={{ textAlign: 'center' }}>
          <p style={{ color: 'red' }}>❌ {error}</p>
          <button onClick={reset}>↩ Spróbuj ponownie</button>
        </div>
      )}
    </main>
  )
}
