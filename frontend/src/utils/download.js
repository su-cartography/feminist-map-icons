/** Download helpers for the icon detail page. */

export function triggerDownload(url, filename) {
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.rel = 'noopener'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

export function saveBlob(blob, filename) {
  const file =
    blob.type && blob.type !== 'application/octet-stream'
      ? new Blob([blob], { type: 'application/octet-stream' })
      : blob
  const objectUrl = URL.createObjectURL(file)
  triggerDownload(objectUrl, filename)
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1000)
}

export async function saveFile(blob, filename) {
  if (window.showSaveFilePicker) {
    try {
      const ext = filename.includes('.')
        ? filename.slice(filename.lastIndexOf('.'))
        : ''
      const handle = await window.showSaveFilePicker({
        suggestedName: filename,
        types: ext
          ? [
              {
                description: 'File',
                accept: { [blob.type || 'application/octet-stream']: [ext] },
              },
            ]
          : undefined,
      })
      const writable = await handle.createWritable()
      await writable.write(blob)
      await writable.close()
      return
    } catch (err) {
      if (err.name === 'AbortError') return
    }
  }
  saveBlob(blob, filename)
}
