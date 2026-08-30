# Multipart File Upload → Python Bridge Pattern

Pattern for uploading Excel/CSV files from a React frontend through Next.js to a Python processing bridge.

## Data Flow

```
UploadZone (React)
    │ POST /api/upload (multipart/form-data)
    ▼
Next.js Route Handler
    │ 1. Save file to os.tmpdir()
    │ 2. Call bridge.py --action upload.allocation --filepath <temp>
    │ 3. Clean up temp file
    ▼
bridge.py
    │ 1. pl.read_excel(filepath)
    │ 2. Validate required columns
    │ 3. Column rename mapping
    │ 4. Store DataFrame as Parquet in session
    │ 5. Return summary JSON
    ▼
UploadZone receives { success, summary, warnings }
```

## Client-side Upload Component

```tsx
"use client"

import { useState, useCallback } from "react"
import { ArrowUpTrayIcon, CheckCircleIcon, ExclamationCircleIcon } from "@heroicons/react/24/outline"

interface UploadZoneProps {
  type: "allocation" | "workstream"
  sessionId: string
  onUpload: (result: UploadResult) => void
}

export function UploadZone({ type, sessionId, onUpload }: UploadZoneProps) {
  const [state, setState] = useState<"idle" | "uploading" | "success" | "error">("idle")
  const [message, setMessage] = useState("")

  const handleUpload = useCallback(async (file: File) => {
    setState("uploading")
    setMessage(`Uploading ${file.name}...`)

    const formData = new FormData()
    formData.append("file", file)
    formData.append("sessionId", sessionId)
    formData.append("fileType", type)

    try {
      const response = await fetch("/api/upload", { method: "POST", body: formData })
      const result: UploadResult = await response.json()
      if (result.success) {
        setState("success")
        setMessage(`Uploaded: ${result.summary?.total_rows} rows loaded`)
        onUpload(result)
      } else {
        setState("error")
        setMessage(result.error || "Upload failed")
      }
    } catch (err) {
      setState("error")
      setMessage(err instanceof Error ? err.message : "Upload failed")
    }
  }, [type, sessionId, onUpload])

  // ... drag-and-drop handlers, visual state rendering
}
```

## Next.js Upload Route Handler

```typescript
// app/api/upload/route.ts
import { NextRequest, NextResponse } from "next/server";
import { execFileSync } from "child_process";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";

export async function POST(request: NextRequest) {
  const formData = await request.formData();
  const file = formData.get("file") as File | null;
  const sessionId = formData.get("sessionId") as string | null;
  const fileType = formData.get("fileType") as string | null;

  if (!file || !sessionId || !["allocation", "workstream"].includes(fileType || "")) {
    return NextResponse.json({ success: false, error: "Missing fields" }, { status: 400 });
  }

  // Validate extension and size
  const ext = path.extname(file.name).toLowerCase();
  if (![".xlsx", ".xls", ".csv"].includes(ext)) {
    return NextResponse.json({ success: false, error: "Only .xlsx/.xls files" }, { status: 400 });
  }
  if (file.size > 10 * 1024 * 1024) {
    return NextResponse.json({ success: false, error: "Max 10MB" }, { status: 400 });
  }

  // Save to temp, call bridge, clean up
  const tempPath = path.join(os.tmpdir(), `beacon_${sessionId}_${fileType}${ext}`);
  const buffer = Buffer.from(await file.arrayBuffer());
  fs.writeFileSync(tempPath, buffer);

  const stdout = execFileSync("python3", [BRIDGE_PATH, "--action", `upload.${fileType}`,
    "--session", sessionId, "--filepath", tempPath],
    { encoding: "utf-8", timeout: 60000 });
  fs.unlinkSync(tempPath);

  return NextResponse.json(JSON.parse(stdout.trim()));
}
```

## Session Management

Sessions are created separately from uploads. Pattern:

```tsx
// Client side — create session on mount
useEffect(() => {
  fetch("/api/session", { method: "POST" })
    .then(r => r.json())
    .then(data => {
      if (data.session_id) setSessionId(data.session_id)
    })
}, [])
```

```typescript
// Server side (app/api/session/route.ts)
export async function POST() {
  const stdout = execFileSync("python3", [BRIDGE_PATH, "--action", "session.create"],
    { encoding: "utf-8", timeout: 30000 });
  return NextResponse.json(JSON.parse(stdout.trim()));
}
```

## Session Store for Bridge (file-backed)

```python
# File-backed, not in-memory — each bridge call is a fresh process
class Session:
    def get_allocation(self) -> pl.DataFrame | None:
        if self.allocation_path.exists():
            return pl.read_parquet(self.allocation_path)
        return None

    def set_allocation(self, df: pl.DataFrame, filename: str) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        df.write_parquet(self.allocation_path)
```

## Testing the Upload Flow

```python
# Python test — construct multipart manually
boundary = "----TestBoundary"
lines = [
    f"--{boundary}".encode(),
    b'Content-Disposition: form-data; name="file"; filename="test.xlsx"',
    b"Content-Type: application/octet-stream",
    b"",
    file_bytes,
    f"--{boundary}".encode(),
    b'Content-Disposition: form-data; name="sessionId"',
    b"",
    sid.encode(),
    f"--{boundary}".encode(),
    b'Content-Disposition: form-data; name="fileType"',
    b"",
    b"allocation",
    f"--{boundary}--".encode(),
]
body = b"\r\n".join(lines)
# Upload via curl or urllib
```

## Error Handling Checklist

- [ ] File too large (>10MB) — return 400 with message
- [ ] Wrong extension — return 400 with message
- [ ] Missing fields (file, sessionId, fileType) — return 400
- [ ] Invalid fileType (not "allocation" or "workstream") — return 400
- [ ] Excel parse error — bridge returns `{success: false, error: "..."}` 
- [ ] Missing required columns — bridge validates and returns error
- [ ] Session not found — upload creates session if it doesn't exist (permissive)
- [ ] Bridge timeout (>60s) — catch in execFileSync and handle
- [ ] Temp file cleanup failure — non-fatal, log and continue
