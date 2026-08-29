import { useState } from 'react'
import { FileUpload } from './components/FileUpload'
import { VideoPreview } from './components/VideoPreview'
import { PerspectiveCalibrator } from './components/PerspectiveCalibrator'
import { HeatmapMenu } from './components/HeatmapMenu'
import { HeatmapGrid } from './components/HeatmapGrid'
import { cn } from '@sglara/cn'
import { uploadVideo, createHeatmapJob, submitCalibration, ApiRequestError } from './api/client'
import { describeHeatmapRequest } from './utils/describeHeatmapRequest'
import { describeComposedLayers } from './utils/describeComposedLayers'
import type { AppState, HeatmapJobRequest, HeatmapTileData, Point } from './types'

const SESSION_STORAGE_KEY = 'heatmaps.session'

interface Session {
  videoId: string
  videoUrl: string
  tiles: HeatmapTileData[]
}

function loadSession(): Session | null {
  const raw = sessionStorage.getItem(SESSION_STORAGE_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as Session
  } catch {
    return null
  }
}

function saveSession(session: Session | null) {
  if (session) {
    sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session))
  } else {
    sessionStorage.removeItem(SESSION_STORAGE_KEY)
  }
}

export default function App() {
  const [session, setSession] = useState<Session | null>(loadSession)
  const [appState, setAppState] = useState<AppState>(() => (session ? 'READY' : 'IDLE'))
  const [error, setError] = useState<string | null>(null)
  const [addError, setAddError] = useState<string | null>(null)
  const [calibrationError, setCalibrationError] = useState<string | null>(null)
  const [layout, setLayout] = useState<'grid' | 'list'>('grid')
  const [editMode, setEditMode] = useState<'normal' | 'edit'>('normal')

  const reset = () => {
    saveSession(null)
    setSession(null)
    setAppState('IDLE')
    setError(null)
    setAddError(null)
    setCalibrationError(null)
  }

  const handleUpload = async (file: File) => {
    setAppState('UPLOADING')
    setError(null)
    try {
      const { video_id, video_url } = await uploadVideo(file)
      const newSession: Session = { videoId: video_id, videoUrl: video_url, tiles: [] }
      saveSession(newSession)
      setSession(newSession)
      setAppState('CALIBRATING')
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Błąd wysyłania pliku')
      setAppState('ERROR')
    }
  }

  const handleCalibrationSubmit = async (cameraPoints: Point[], realWorldPoints: Point[]) => {
    if (!session) return
    setCalibrationError(null)
    try {
      await submitCalibration(session.videoId, {
        camera_points: cameraPoints,
        real_world_points: realWorldPoints,
      })
      setAppState('READY')
    } catch (err) {
      setCalibrationError(err instanceof ApiRequestError ? err.message : 'Nie udało się zapisać kalibracji')
    }
  }

  const handleCalibrationSkip = () => {
    setAppState('READY')
  }

  const handleAddHeatmap = async (request: HeatmapJobRequest, customName?: string) => {
    if (!session) return
    setAddError(null)
    try {
      const { job_id } = await createHeatmapJob(session.videoId, request)
      const label =
        customName ??
        (request.type === 'composed' ? describeComposedLayers(request.layers) : describeHeatmapRequest(request))
      const newSession: Session = {
        ...session,
        tiles: [...session.tiles, { jobId: job_id, label }],
      }
      saveSession(newSession)
      setSession(newSession)
    } catch (err) {
      setAddError(err instanceof ApiRequestError ? err.message : 'Nie udało się dodać analizy')
    }
  }

  const handleDeleteTile = (jobId: string) => {
    if (!session) return
    const newSession: Session = {
      ...session,
      tiles: session.tiles.filter((tile) => tile.jobId !== jobId),
    }
    saveSession(newSession)
    setSession(newSession)
  }

  return (
    <main className="flex flex-col items-center gap-8 min-h-screen p-8">
      <h1 className="text-3xl font-semibold">Analiza Wideo</h1>

      {appState === 'IDLE' && (
        <FileUpload onUpload={handleUpload} />
      )}

      {appState === 'UPLOADING' && (
        <p>⏳ Wysyłanie pliku...</p>
      )}

      {appState === 'CALIBRATING' && session && (
        <PerspectiveCalibrator
          videoUrl={session.videoUrl}
          onSubmit={handleCalibrationSubmit}
          onSkip={handleCalibrationSkip}
          error={calibrationError}
        />
      )}

      {appState === 'READY' && session && (
        <>
          <VideoPreview videoUrl={session.videoUrl} />

          <HeatmapMenu videoUrl={session.videoUrl} onAdd={handleAddHeatmap} />
          {addError && <p className="text-red-600">❌ {addError}</p>}

          <div className="flex flex-row gap-2">
            <button
                onClick={() => setLayout((l) => (l === 'grid' ? 'list' : 'grid'))}
                className="inline-flex items-center justify-center rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {layout === 'grid' ? '☰ Widok listy' : '▦ Widok siatki'}
            </button>

            <button
                onClick={() => setEditMode((l) => (l === 'normal' ? 'edit' : 'normal'))}
                className={cn("inline-flex", "items-center", "justify-center", "rounded-md", "border", "border-gray-300", "px-3", "py-1.5", "text-sm", "font-medium", "disabled:opacity-50", "disabled:cursor-not-allowed", editMode === 'edit' ? 'bg-red-900 text-white' : 'hover:bg-gray-50')}
            >
              {editMode === 'normal' ? '️🗑 Tryb edytowania' : '👁️ Tryb przeglądania'}
            </button>

          </div>

          <HeatmapGrid tiles={session.tiles} layout={layout} editMode={editMode} onDelete={handleDeleteTile} />

          <button
            onClick={reset}
            className="inline-flex items-center justify-center rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ↩ Nowe wideo
          </button>
        </>
      )}

      {appState === 'ERROR' && (
        <div className="text-center">
          <p className="text-red-600">❌ {error}</p>
          <button
            onClick={reset}
            className="inline-flex items-center justify-center rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ↩ Spróbuj ponownie
          </button>
        </div>
      )}
    </main>
  )
}
