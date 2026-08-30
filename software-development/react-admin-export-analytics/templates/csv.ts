/**
 * Client-side CSV export helper for React admin consoles.
 * Copy verbatim to src/lib/csv.ts. Zero dependencies.
 *
 * - toCsv: RFC 4180 escaping (quotes fields containing , " \n \r, doubles embedded quotes),
 *   CRLF line endings.
 * - downloadCsv: prepends a UTF-8 BOM so Excel opens accented/unicode text correctly,
 *   builds a Blob, triggers a download click, revokes the object URL.
 */

/** Escape a CSV field per RFC 4180. */
function escapeField(value: string): string {
  if (value.includes(',') || value.includes('"') || value.includes('\n') || value.includes('\r')) {
    return '"' + value.replace(/"/g, '""') + '"'
  }
  return value
}

/** Serialize rows (array of string arrays) into a CSV string with header. */
export function toCsv(headers: string[], rows: string[][]): string {
  const lines = [headers.map(escapeField).join(',')]
  for (const row of rows) {
    lines.push(row.map(escapeField).join(','))
  }
  return lines.join('\r\n')
}

/** Trigger a browser download of a CSV string. */
export function downloadCsv(filename: string, csv: string): void {
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
