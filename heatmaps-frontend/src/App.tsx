import { useState, useEffect, useRef, useCallback } from 'react'
import { FileUpload } from './components/FileUpload'
import { JobStatus } from './components/JobStatus'
import { VideoPlayerGrid } from './components/VideoPlayerGrid'
import { uploadVideo, getJobStatus, UploadError } from './api/client'
import { openSSEStream } from './api/sseStream'
import type { AppState, HeatmapType, VideoOutput } from './types'
import './App.css'

const JOB_ID_STORAGE_KEY = 'heatmaps.jobId'

export default function App() {
  const [appState, setAppState] = useState<AppState>('IDLE')
  const [progress, setProgress] = useState(0)
  const [outputs, setOutputs] = useState<VideoOutput[]>([])
  const [error, setError] = useState<string | null>(null)
  const sseRef = useRef<EventSource | null>(null)

  const connectStream = useCallback((jobId: string) => {
    const es = openSSEStream(
      jobId,
      (event) => {
        if (event.status === 'queued') {
          setProgress(0)
        } else if (event.status === 'processing') {
          setProgress(event.progress ?? 0)
        } else if (event.status === 'completed') {
          es.close()
          sseRef.current = null
          setProgress(100)
          setOutputs(event.outputs ?? [])
          setAppState('READY_TO_PLAY')
        } else if (event.status === 'failed') {
          es.close()
          sseRef.current = null
          sessionStorage.removeItem(JOB_ID_STORAGE_KEY)
          setError(event.error ?? 'Przetwarzanie nie powiodło się')
          setAppState('ERROR')
        }
      },
      () => {
        setError('Utracono połączenie SSE')
        setAppState('ERROR')
      },
    )
    sseRef.current = es
  }, [])

  // Recover state after a page reload if a job was in flight.
  useEffect(() => {
    const jobId = sessionStorage.getItem(JOB_ID_STORAGE_KEY)
    if (!jobId) return

    getJobStatus(jobId)
      .then((snapshot) => {
        if (snapshot.status === 'completed') {
          setProgress(100)
          setOutputs(snapshot.outputs ?? [])
          setAppState('READY_TO_PLAY')
        } else if (snapshot.status === 'failed') {
          sessionStorage.removeItem(JOB_ID_STORAGE_KEY)
          setError(snapshot.error ?? 'Przetwarzanie nie powiodło się')
          setAppState('ERROR')
        } else {
          setProgress(snapshot.status === 'processing' ? snapshot.progress ?? 0 : 0)
          setAppState('PROCESSING')
          connectStream(jobId)
        }
      })
      .catch(() => {
        sessionStorage.removeItem(JOB_ID_STORAGE_KEY)
      })
    // Only run once on mount — connectStream is stable (empty dep array).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Cleanup SSE on unmount
  useEffect(() => {
    return () => {
      sseRef.current?.close()
    }
  }, [])

  const reset = () => {
    sseRef.current?.close()
    sseRef.current = null
    sessionStorage.removeItem(JOB_ID_STORAGE_KEY)
    setAppState('IDLE')
    setProgress(0)
    setOutputs([])
    setError(null)
  }

  const handleUpload = async (file: File, heatmapTypes: HeatmapType[]) => {
    setAppState('UPLOADING')
    setError(null)
    try {
      const { job_id } = await uploadVideo(file, heatmapTypes)
      sessionStorage.setItem(JOB_ID_STORAGE_KEY, job_id)
      setAppState('PROCESSING')
      setProgress(0)
      connectStream(job_id)
    } catch (err) {
      setError(err instanceof UploadError ? err.message : 'Błąd wysyłania pliku')
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
