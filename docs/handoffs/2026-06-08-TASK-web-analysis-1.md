# WEB-ANALYSIS-1 — Capture & Analysis Panel (browser camera)

**Date:** 2026-06-09 (revision 3)  
**Layer:** `frontend/src/App.tsx` + `frontend/src/api.ts` + `frontend/src/types.ts`  
**Backend changes required:** None — все эндпоинты уже существуют.  
**Prerequisite:** WORKER-FIX-1 выполнен.  
**Review agent:** `backend-reviewer` (URL-пути), `security-reviewer` (getUserMedia permissions, canvas data)

---

## Goal

Заменить placeholder на странице "Анализы" на полноценную панель захвата кадров с камеры и запуска анализа.

**Поток:**
1. Выбрать карьер → паспорт (только APPROVED / ACTIVE)
2. Выбрать камеру из браузера → живой превью
3. Сделать один или несколько снимков → просмотреть миниатюры, удалить плохие
4. Нажать "Отправить на анализ" → автоматически создаётся сессия, кадры загружаются, job ставится в очередь
5. Polling статуса → результат P80 + ссылка на отчёт

---

## Контекст: ZED 2 как обычная стереокамера

ZED 2 без ZED SDK на Windows определяется браузером как **одно устройство** с одним видео-потоком.  
Драйвер склеивает оба глаза в **SBS (side-by-side) кадр**: левая половина = left eye, правая = right eye.  

Пример: разрешение потока `2560×720` → левый кадр `1280×720`, правый кадр `1280×720`.

Признак SBS-режима: **соотношение сторон видео-потока > 1.8** (16:9 ≈ 1.78; SBS ≈ 2:1 или 3.6:1).  
При SBS: JS автоматически режет кадр пополам и загружает как `left_frame` + `right_frame`.  
При обычной камере: загружается только `left_frame`.

---

## Acceptance criteria

- [ ] `tsc --noEmit` 0 ошибок
- [ ] Passport selector: показывает только APPROVED/ACTIVE паспорта выбранного карьера
- [ ] `navigator.mediaDevices.enumerateDevices()` — список камер в dropdown
- [ ] `getUserMedia` запускается при выборе камеры → `<video>` показывает живой поток
- [ ] "Сделать снимок" — canvas.drawImage → blob → добавляется в галерею
- [ ] SBS: если `videoWidth / videoHeight > 1.8` → автосплит на left+right (два тайла в галерее)
- [ ] Кнопка "Удалить" на каждом тайле убирает его из галереи
- [ ] "Отправить на анализ" активна только при: паспорт выбран + ≥1 кадр в галерее
- [ ] Все кадры загружаются с правильным `frame_index` (0, 1, 2…)
- [ ] SBS right-кадры загружаются как `artifact_type=right_frame` с тем же `frame_index`
- [ ] Polling 3 с, `clearInterval` при размонтировании
- [ ] Completed: P80, кнопка "Открыть отчёт" → screen `reports`
- [ ] Видео-поток остановлен (`stream.getTracks().forEach(t => t.stop())`) при уходе со страницы

---

## Типы для `types.ts`

```ts
// Новые типы — добавить к существующим

export interface Device {
  id: string;
  serial_number: string;
  model: string;
  firmware_version: string | null;
  notes: string | null;
}

export interface Calibration {
  id: string;
  device_id: string;
  baseline_mm: number;
  image_width_px: number;
  image_height_px: number;
  is_active: boolean;
  created_at: string;
}

export interface CaptureSession {
  id: string;
  blast_event_id: string;
  device_id: string;
  calibration_id: string;
  captured_by_id: string;
  capture_datetime: string;
  frame_count: number;
  notes: string | null;
}

export interface AnalysisJob {
  id: string;
  capture_session_id: string;
  model_version_id: string | null;
  status: string; // queued | running | completed | failed
  queued_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  pipeline_log: Record<string, unknown> | null;
}

export interface Artifact {
  id: string;
  capture_session_id: string;
  artifact_type: string;
  storage_bucket: string;
  storage_key: string;
  file_size_bytes: number | null;
  content_type: string | null;
  frame_index: number | null;
}

// Локальный тип (не хранится в БД)
export interface CapturedFrame {
  id: string;               // uuid4() на клиенте
  blob: Blob;
  dataUrl: string;          // для <img src>
  width: number;
  height: number;
  artifactType: 'left_frame' | 'right_frame';
  frameIndex: number;       // порядковый номер в сессии
  capturedAt: number;       // Date.now()
}
```

---

## API helpers для `api.ts`

Добавить в `api`:

```ts
devices: {
  list: () => get<Paginated<Device>>('/devices').then((p) => p.items),
  create: (body: { serial_number: string; model: string; firmware_version?: string | null }) =>
    post<Device>('/devices', body),
  listCalibrations: (deviceId: string) =>
    get<Paginated<Calibration>>(`/devices/${deviceId}/calibrations`).then((p) => p.items),
  addCalibration: (deviceId: string, body: Record<string, unknown>) =>
    post<Calibration>(`/devices/${deviceId}/calibrations`, body),
},

captureFlow: {
  createSession: (
    quarryId: string,
    passportId: string,
    body: { device_id: string; calibration_id: string },
  ) =>
    post<CaptureSession>(
      `/quarries/${quarryId}/passports/${passportId}/blast-event/capture-sessions`,
      body,
    ),

  // multipart — НЕ указывать Content-Type (браузер ставит boundary сам)
  uploadArtifact: async (
    sessionId: string,
    file: File,
    artifactType: 'left_frame' | 'right_frame',
    frameIndex: number,
  ): Promise<Artifact> => {
    const formData = new FormData();
    formData.append('artifact_type', artifactType);
    formData.append('frame_index', String(frameIndex));
    formData.append('file', file);
    const headers = await authHeader(); // Content-Type сюда НЕ добавлять
    const res = await fetch(`${API_BASE}/v1/capture-sessions/${sessionId}/artifacts`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json() as Promise<Artifact>;
  },

  enqueueJob: (sessionId: string) =>
    post<AnalysisJob>(`/captures/${sessionId}/jobs`, {}),

  pollJob: (sessionId: string, jobId: string) =>
    get<AnalysisJob>(`/captures/${sessionId}/jobs/${jobId}`),

  getJobResult: (sessionId: string, jobId: string) =>
    get<AnalysisResult>(`/captures/${sessionId}/jobs/${jobId}/result`),
},
```

> **Критично:** job эндпоинты — `/api/v1/captures/` (не `/capture-sessions/`). Источник: `backend/app/main.py`.

---

## Вспомогательные функции (в компоненте или рядом)

### Захват кадра с video-элемента

```tsx
function captureFrameFromVideo(
  video: HTMLVideoElement,
): { left: { blob: Blob; dataUrl: string }; right: { blob: Blob; dataUrl: string } | null } {
  const w = video.videoWidth;
  const h = video.videoHeight;
  const isSbs = w / h > 1.8;

  const canvas = document.createElement('canvas');
  const ctx2d = canvas.getContext('2d')!;

  if (isSbs) {
    const halfW = Math.floor(w / 2);

    // Left half
    canvas.width = halfW;
    canvas.height = h;
    ctx2d.drawImage(video, 0, 0, halfW, h, 0, 0, halfW, h);
    const leftDataUrl = canvas.toDataURL('image/jpeg', 0.92);
    const leftBlob = dataUrlToBlob(leftDataUrl);

    // Right half
    ctx2d.clearRect(0, 0, halfW, h);
    ctx2d.drawImage(video, halfW, 0, halfW, h, 0, 0, halfW, h);
    const rightDataUrl = canvas.toDataURL('image/jpeg', 0.92);
    const rightBlob = dataUrlToBlob(rightDataUrl);

    return {
      left: { blob: leftBlob, dataUrl: leftDataUrl },
      right: { blob: rightBlob, dataUrl: rightDataUrl },
    };
  } else {
    canvas.width = w;
    canvas.height = h;
    ctx2d.drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
    return { left: { blob: dataUrlToBlob(dataUrl), dataUrl }, right: null };
  }
}

function dataUrlToBlob(dataUrl: string): Blob {
  const [header, b64] = dataUrl.split(',');
  const mime = header.match(/:(.*?);/)![1];
  const bytes = atob(b64);
  const arr = new Uint8Array(bytes.length);
  for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
  return new Blob([arr], { type: mime });
}
```

---

## Стейт `AnalysesPage`

```tsx
// Passport selection
const [analysisPassportId, setAnalysisPassportId] = useState<string | null>(null);
const [analysisPassports, setAnalysisPassports] = useState<BlastPassport[]>([]);

// Browser camera
const [browserCameras, setBrowserCameras] = useState<MediaDeviceInfo[]>([]);
const [selectedCamId, setSelectedCamId] = useState<string | null>(null);
const [stream, setStream] = useState<MediaStream | null>(null);
const [isSbs, setIsSbs] = useState(false);
const videoRef = useRef<HTMLVideoElement>(null);

// Captured frames gallery
const [frames, setFrames] = useState<CapturedFrame[]>([]);
const [nextFrameIndex, setNextFrameIndex] = useState(0);

// Launch state machine
type LaunchState = 'idle' | 'uploading' | 'enqueued' | 'polling' | 'completed' | 'failed';
const [launchState, setLaunchState] = useState<LaunchState>('idle');
const [launchStep, setLaunchStep] = useState('');
const [currentJob, setCurrentJob] = useState<AnalysisJob | null>(null);
const [jobResult, setJobResult] = useState<AnalysisResult | null>(null);
const [sessionId, setSessionId] = useState<string | null>(null);
const [launchError, setLaunchError] = useState<string | null>(null);
const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

// Stop stream and polling on unmount or screen change
useEffect(() => {
  return () => {
    stream?.getTracks().forEach((t) => t.stop());
    if (pollRef.current) clearInterval(pollRef.current);
  };
}, [stream]);
```

---

## Загрузка данных при монтировании

```tsx
// Load cameras
useEffect(() => {
  if (!kc.authenticated) return;
  navigator.mediaDevices
    .enumerateDevices()
    .then((devs) => setBrowserCameras(devs.filter((d) => d.kind === 'videoinput')))
    .catch(() => setBrowserCameras([]));
}, [kc.authenticated]);

// Load passports for selected quarry (only APPROVED / ACTIVE)
useEffect(() => {
  if (!selectedQuarryId) { setAnalysisPassports([]); return; }
  api.passports.list(selectedQuarryId).then((all) =>
    setAnalysisPassports(
      all.filter((p) => ['approved', 'active'].includes(p.status.toLowerCase())),
    ),
  ).catch(() => setAnalysisPassports([]));
}, [selectedQuarryId]);
```

---

## Запуск камеры при выборе

```tsx
async function handleSelectCamera(deviceId: string) {
  // Stop previous stream
  stream?.getTracks().forEach((t) => t.stop());
  setStream(null);
  setSelectedCamId(deviceId);
  setIsSbs(false);

  try {
    const newStream = await navigator.mediaDevices.getUserMedia({
      video: { deviceId: { exact: deviceId } },
    });
    setStream(newStream);
    if (videoRef.current) {
      videoRef.current.srcObject = newStream;
      videoRef.current.play().catch(() => {});
      // Detect SBS after metadata loads
      videoRef.current.onloadedmetadata = () => {
        const vw = videoRef.current!.videoWidth;
        const vh = videoRef.current!.videoHeight;
        setIsSbs(vw / vh > 1.8);
      };
    }
  } catch (err) {
    setLaunchError(`Нет доступа к камере: ${err instanceof Error ? err.message : String(err)}`);
  }
}
```

---

## Захват снимка

```tsx
function handleCapture() {
  if (!videoRef.current || !stream) return;
  const { left, right } = captureFrameFromVideo(videoRef.current);
  const id = crypto.randomUUID();
  const idx = nextFrameIndex;

  const newFrames: CapturedFrame[] = [
    {
      id,
      blob: left.blob,
      dataUrl: left.dataUrl,
      width: videoRef.current.videoWidth / (right ? 2 : 1),
      height: videoRef.current.videoHeight,
      artifactType: 'left_frame',
      frameIndex: idx,
      capturedAt: Date.now(),
    },
  ];

  if (right) {
    newFrames.push({
      id: crypto.randomUUID(),
      blob: right.blob,
      dataUrl: right.dataUrl,
      width: videoRef.current.videoWidth / 2,
      height: videoRef.current.videoHeight,
      artifactType: 'right_frame',
      frameIndex: idx,
      capturedAt: Date.now(),
    });
  }

  setFrames((prev) => [...prev, ...newFrames]);
  setNextFrameIndex((n) => n + 1);
}

function handleDeleteFrame(frameId: string) {
  setFrames((prev) => prev.filter((f) => f.id !== frameId));
}
```

---

## Launch handler

```tsx
async function handleLaunch() {
  if (!selectedQuarryId || !analysisPassportId) return;
  const leftFrames = frames.filter((f) => f.artifactType === 'left_frame');
  if (leftFrames.length === 0) return;

  setLaunchError(null);
  setCurrentJob(null);
  setJobResult(null);

  try {
    // Step 1: ZMetrics device + calibration (auto-select first in DB)
    setLaunchStep('Получаю данные устройства...');
    setLaunchState('uploading');
    const devices = await api.devices.list();
    if (devices.length === 0) {
      throw new Error(
        'Нет устройств в системе. Запустите dev-seed: POST /api/v1/admin/dev-seed',
      );
    }
    const device = devices[0];
    const cals = await api.devices.listCalibrations(device.id);
    if (cals.length === 0) {
      throw new Error('Нет калибровок для устройства. Запустите dev-seed.');
    }
    const cal = cals[0];

    // Step 2: blast event (create if not exists)
    setLaunchStep('Проверяю запись взрыва...');
    try {
      await api.blastEvents.get(selectedQuarryId, analysisPassportId);
    } catch {
      await api.blastEvents.create(selectedQuarryId, analysisPassportId, {
        blast_datetime: new Date().toISOString(),
      });
    }

    // Step 3: capture session
    setLaunchStep('Создаю сессию съёмки...');
    const session = await api.captureFlow.createSession(selectedQuarryId, analysisPassportId, {
      device_id: device.id,
      calibration_id: cal.id,
    });
    setSessionId(session.id);

    // Step 4: upload all frames
    const allFrames = frames; // snapshot before state might change
    for (const frame of allFrames) {
      setLaunchStep(`Загружаю ${frame.artifactType} #${frame.frameIndex}...`);
      const file = new File([frame.blob], `${frame.artifactType}_${frame.frameIndex}.jpg`, {
        type: 'image/jpeg',
      });
      await api.captureFlow.uploadArtifact(
        session.id,
        file,
        frame.artifactType,
        frame.frameIndex,
      );
    }

    // Step 5: enqueue job
    setLaunchStep('Ставлю задачу в очередь...');
    const job = await api.captureFlow.enqueueJob(session.id);
    setCurrentJob(job);
    setLaunchState('enqueued');
    startPolling(session.id, job.id);

  } catch (err) {
    setLaunchError(err instanceof Error ? err.message : String(err));
    setLaunchState('failed');
  }
}

function startPolling(sid: string, jid: string) {
  setLaunchState('polling');
  pollRef.current = setInterval(async () => {
    try {
      const j = await api.captureFlow.pollJob(sid, jid);
      setCurrentJob(j);
      if (j.status === 'completed') {
        clearInterval(pollRef.current!); pollRef.current = null;
        try {
          const result = await api.captureFlow.getJobResult(sid, j.id);
          setJobResult(result);
        } catch { /* result not yet written — show completed without P80 */ }
        setLaunchState('completed');
      } else if (j.status === 'failed') {
        clearInterval(pollRef.current!); pollRef.current = null;
        setLaunchError(j.error_message ?? 'Ошибка воркера');
        setLaunchState('failed');
      }
    } catch { /* network error — keep polling */ }
  }, 3000);
}

function handleReset() {
  if (pollRef.current) clearInterval(pollRef.current);
  setLaunchState('idle');
  setLaunchStep('');
  setCurrentJob(null);
  setJobResult(null);
  setSessionId(null);
  setLaunchError(null);
  setFrames([]);
  setNextFrameIndex(0);
}
```

---

## Рендер (заменить содержимое AnalysesPage)

```tsx
const isBusy = !['idle', 'completed', 'failed'].includes(launchState);
const hasLeftFrame = frames.some((f) => f.artifactType === 'left_frame');
const canLaunch = !!selectedQuarryId && !!analysisPassportId && hasLeftFrame && !isBusy;
const isMock = JSON.stringify(currentJob?.pipeline_log ?? {}).toLowerCase().includes('synthetic');

return (
  <div className="screen">
    <div className="workspace">
      <h2>Анализ развала — захват с камеры</h2>

      {/* ── 1. ПАСПОРТ ── */}
      <section className="form-section">
        <h3>1. Паспорт</h3>
        {/* Quarry selector — reuse existing pattern from App.tsx */}
        <div className="form-row">
          <label>Карьер</label>
          <select
            value={selectedQuarryId ?? ''}
            onChange={(e) => { setSelectedQuarryId(e.target.value || null); setAnalysisPassportId(null); }}
            disabled={isBusy}
          >
            <option value="">— выберите карьер —</option>
            {quarries.map((q) => <option key={q.id} value={q.id}>{q.name}</option>)}
          </select>
        </div>
        <div className="form-row">
          <label>Паспорт</label>
          <select
            value={analysisPassportId ?? ''}
            onChange={(e) => setAnalysisPassportId(e.target.value || null)}
            disabled={!selectedQuarryId || isBusy}
          >
            <option value="">— выберите паспорт (APPROVED / ACTIVE) —</option>
            {analysisPassports.map((p) => (
              <option key={p.id} value={p.id}>
                #{p.revision_number} · {p.status} · P80 цель: {p.target_p80_mm ?? '—'} мм
              </option>
            ))}
          </select>
          {selectedQuarryId && analysisPassports.length === 0 && (
            <span style={{ fontSize: 12, color: '#e87' }}>
              Нет паспортов APPROVED/ACTIVE. Перейдите в Паспорта и утвердите паспорт.
            </span>
          )}
        </div>
      </section>

      {/* ── 2. КАМЕРА ── */}
      <section className="form-section">
        <h3>2. Камера</h3>
        <div className="form-row">
          <label>Устройство</label>
          <select
            value={selectedCamId ?? ''}
            onChange={(e) => { if (e.target.value) void handleSelectCamera(e.target.value); }}
            disabled={isBusy}
          >
            <option value="">— выберите камеру —</option>
            {browserCameras.map((c) => (
              <option key={c.deviceId} value={c.deviceId}>
                {c.label || `Camera ${c.deviceId.slice(0, 8)}`}
              </option>
            ))}
          </select>
          {browserCameras.length === 0 && (
            <span style={{ fontSize: 12, color: '#e87' }}>
              Камеры не найдены. Разрешите доступ к камере в браузере.
            </span>
          )}
        </div>

        {stream && (
          <div style={{ marginTop: 8 }}>
            {isSbs && (
              <p style={{ fontSize: 12, color: '#4a9', margin: '4px 0' }}>
                ✓ Обнаружен SBS-режим (ZED 2) — кадр будет автоматически разделён на left+right
              </p>
            )}
            <video
              ref={videoRef}
              autoPlay
              muted
              playsInline
              style={{ maxWidth: '100%', maxHeight: 300, background: '#000', display: 'block' }}
            />
            <button
              className="primary"
              style={{ marginTop: 8 }}
              onClick={handleCapture}
              disabled={isBusy}
            >
              📸 Сделать снимок {isSbs ? '(stereo)' : ''}
            </button>
          </div>
        )}
      </section>

      {/* ── 3. ГАЛЕРЕЯ КАДРОВ ── */}
      {frames.length > 0 && (
        <section className="form-section">
          <h3>3. Кадры ({frames.length})</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {frames.map((f) => (
              <div
                key={f.id}
                style={{
                  position: 'relative',
                  border: '1px solid #ddd',
                  borderRadius: 4,
                  overflow: 'hidden',
                  width: 140,
                }}
              >
                <img
                  src={f.dataUrl}
                  alt={`${f.artifactType} #${f.frameIndex}`}
                  style={{ width: 140, height: 80, objectFit: 'cover', display: 'block' }}
                />
                <div style={{ fontSize: 11, padding: '2px 4px', background: '#f5f5f5' }}>
                  {f.artifactType === 'left_frame' ? 'L' : 'R'} #{f.frameIndex}
                </div>
                <button
                  onClick={() => handleDeleteFrame(f.id)}
                  disabled={isBusy}
                  style={{
                    position: 'absolute', top: 2, right: 2,
                    background: 'rgba(200,0,0,0.75)', color: '#fff',
                    border: 'none', borderRadius: 2, cursor: 'pointer',
                    padding: '1px 5px', fontSize: 12,
                  }}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── 4. ЗАПУСК ── */}
      <section className="form-section">
        <h3>4. Анализ</h3>
        <div className="form-row">
          {launchState === 'idle' && (
            <button className="primary" disabled={!canLaunch} onClick={() => void handleLaunch()}>
              Отправить на анализ ({frames.filter((f) => f.artifactType === 'left_frame').length} left
              {frames.some((f) => f.artifactType === 'right_frame') ? ' + right' : ''})
            </button>
          )}
          {isBusy && (
            <button className="primary" disabled>Выполняется...</button>
          )}
          {(launchState === 'completed' || launchState === 'failed') && (
            <button className="secondary" onClick={handleReset}>Новый захват</button>
          )}
        </div>

        {/* Progress */}
        {(launchState === 'uploading' || launchState === 'enqueued') && (
          <div className="info-banner"><span className="spinner" /> {launchStep}</div>
        )}
        {launchState === 'polling' && currentJob && (
          <div className="info-banner">
            <span className="spinner" /> Воркер: <strong>{currentJob.status}</strong>
          </div>
        )}

        {/* Result */}
        {launchState === 'completed' && (
          <div className="success-banner">
            ✅ Анализ завершён
            {isMock && <span className="badge-mock"> ⚠ Синтетические данные</span>}
            {jobResult?.p80_mm != null && (
              <div style={{ marginTop: 6 }}>
                P80: <strong>{jobResult.p80_mm.toFixed(0)} мм</strong>
                {jobResult.confidence_score != null && (
                  <> · Уверенность: <strong>{jobResult.confidence_score.toFixed(2)}</strong></>
                )}
              </div>
            )}
            <button
              className="primary"
              style={{ marginTop: 8 }}
              onClick={() => setActiveScreen('reports')}
            >
              Открыть отчёт
            </button>
          </div>
        )}

        {launchState === 'failed' && launchError && (
          <div className="error-banner">❌ {launchError}</div>
        )}

        {/* Debug */}
        {sessionId && (
          <details style={{ marginTop: 12, fontSize: 11, color: '#888' }}>
            <summary>Технические детали</summary>
            <div>Session: {sessionId}</div>
            {currentJob && <div>Job: {currentJob.id} · {currentJob.status}</div>}
            {currentJob?.pipeline_log && (
              <pre style={{ fontSize: 10, maxHeight: 160, overflow: 'auto' }}>
                {JSON.stringify(currentJob.pipeline_log, null, 2)}
              </pre>
            )}
          </details>
        )}
      </section>
    </div>
  </div>
);
```

> `setActiveScreen` — найти в App.tsx существующий паттерн смены экрана и использовать тот же (скорее всего `setActiveScreen` или аналог).

---

## Notes по getUserMedia на localhost

- Chrome/Edge разрешают `getUserMedia` на `localhost` по HTTP (без HTTPS).
- В Docker (nginx): `http://localhost:5173` — работает.
- Если `enumerateDevices()` возвращает камеры без label: нужно сначала вызвать `getUserMedia` с любыми constraints, получить разрешение, и тогда labels появятся. Добавить кнопку "Разрешить доступ к камере" если `browserCameras.every(c => !c.label)`.

---

## Safety

- `parameter_suggestions` не записываются в паспорт
- Passport selector показывает ТОЛЬКО APPROVED/ACTIVE — нельзя запустить анализ на DRAFT
- `⚠ Синтетические данные` при mock pipeline_log
- `stream.getTracks().forEach(t => t.stop())` при уходе со страницы (useEffect cleanup)

---

## Checklist для review-агента

- [ ] `tsc --noEmit` 0 ошибок
- [ ] `stream.getTracks().forEach(t => t.stop())` в useEffect cleanup
- [ ] `pollRef.current` clearInterval в useEffect cleanup  
- [ ] `captureFrameFromVideo`: canvas не утекает (локальная переменная, не DOM)
- [ ] `dataUrlToBlob`: не использует `document.createElement` в loop
- [ ] `passport.status.toLowerCase()` при фильтре (enum может прийти UPPER case)
- [ ] multipart: нет `Content-Type` в headers при uploadArtifact
- [ ] URL job эндпоинтов: `/api/v1/captures/` не `/capture-sessions/`
- [ ] `frame_index` передаётся в `formData.append('frame_index', String(frameIndex))`
- [ ] `getUserMedia` ошибка: показывается понятный текст, не бросается наружу
