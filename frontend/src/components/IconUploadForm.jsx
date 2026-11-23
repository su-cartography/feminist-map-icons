import { useEffect, useId, useState } from 'react'

const MAX_BYTES = 2 * 1024 * 1024

const TEXT_FIELDS = [
  ['primary_tag', 'Primary tag', 'text', 'e.g. park, library'],
  ['designer', 'Designer', 'text', 'Who designed this icon'],
  ['uploader', 'Uploader', 'text', 'Your name or handle'],
  ['icon_geography', 'Icon geography', 'text', 'Place or region'],
  ['icon_description', 'Description', 'textarea', 'What does this icon represent?'],
  ['notes', 'Notes', 'textarea', 'Anything else for reviewers'],
]

function formatApiErrors(data) {
  if (!data || typeof data !== 'object') return 'Upload failed. Try again.'
  if (typeof data.detail === 'string') return data.detail
  const parts = []
  for (const [field, value] of Object.entries(data)) {
    const message = Array.isArray(value) ? value.join(' ') : String(value)
    parts.push(`${field}: ${message}`)
  }
  return parts.join(' ') || 'Upload failed. Try again.'
}

function validateFile(file, kind) {
  if (!file) return ''
  if (file.size > MAX_BYTES) {
    return `${kind.toUpperCase()} is over 2 MB (${(file.size / (1024 * 1024)).toFixed(2)} MB).`
  }
  const name = file.name.toLowerCase()
  if (kind === 'png' && !name.endsWith('.png')) return 'PNG must be a .png file.'
  if (kind === 'svg' && !name.endsWith('.svg')) return 'SVG must be a .svg file.'
  return ''
}

export default function IconUploadForm({ token, username }) {
  const formId = useId()
  const [fields, setFields] = useState({
    primary_tag: '',
    designer: '',
    uploader: username || '',
    icon_geography: '',
    icon_description: '',
    notes: '',
    tag_names: '',
  })
  const [pngFile, setPngFile] = useState(null)
  const [svgFile, setSvgFile] = useState(null)
  const [dragOver, setDragOver] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(null)

  const [pngPreview, setPngPreview] = useState('')

  useEffect(() => {
    if (!pngFile) {
      setPngPreview('')
      return undefined
    }
    const url = URL.createObjectURL(pngFile)
    setPngPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [pngFile])

  function updateField(name, value) {
    setFields((current) => ({ ...current, [name]: value }))
  }

  function assignFile(kind, file) {
    setError('')
    setSuccess(null)
    if (!file) {
      if (kind === 'png') setPngFile(null)
      else setSvgFile(null)
      return
    }
    const problem = validateFile(file, kind)
    if (problem) {
      setError(problem)
      return
    }
    if (kind === 'png') setPngFile(file)
    else setSvgFile(file)
  }

  function onDrop(kind, event) {
    event.preventDefault()
    setDragOver(null)
    const file = event.dataTransfer.files?.[0]
    if (file) assignFile(kind, file)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSuccess(null)

    if (!pngFile && !svgFile) {
      setError('Add at least a PNG or an SVG file.')
      return
    }
    const pngProblem = validateFile(pngFile, 'png')
    const svgProblem = validateFile(svgFile, 'svg')
    if (pngProblem || svgProblem) {
      setError(pngProblem || svgProblem)
      return
    }

    const body = new FormData()
    for (const [key] of TEXT_FIELDS) {
      body.append(key, fields[key].trim())
    }
    const tags = fields.tag_names
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean)
    tags.forEach((tag) => body.append('tag_names', tag))
    if (pngFile) body.append('png_file', pngFile)
    if (svgFile) body.append('svg_file', svgFile)

    setSubmitting(true)
    try {
      const response = await fetch('/api/icons/', {
        method: 'POST',
        headers: { Authorization: `Token ${token}` },
        body,
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        setError(formatApiErrors(data))
        return
      }
      setSuccess({
        uniqueId: data.unique_id,
        status: data.status || 'pending',
      })
      setFields((current) => ({
        ...current,
        primary_tag: '',
        designer: '',
        icon_geography: '',
        icon_description: '',
        notes: '',
        tag_names: '',
        uploader: username || current.uploader,
      }))
      setPngFile(null)
      setSvgFile(null)
    } catch (err) {
      setError(
        err instanceof TypeError
          ? 'Could not reach the server.'
          : 'Upload failed. Try again.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="upload-studio" onSubmit={handleSubmit}>
      <div className="upload-studio__intro">
        <p className="upload-studio__eyebrow">Contributor studio</p>
        <h2>Upload an icon</h2>
        <p>
          Submit PNG and/or SVG with its information. You icon submission will be sent for approval.
        </p>
      </div>

      <div className="upload-drop-grid">
        {['png', 'svg'].map((kind) => {
          const file = kind === 'png' ? pngFile : svgFile
          return (
            <label
              key={kind}
              className={
                dragOver === kind
                  ? `upload-drop is-${kind} is-hot`
                  : `upload-drop is-${kind}`
              }
              onDragOver={(event) => {
                event.preventDefault()
                setDragOver(kind)
              }}
              onDragLeave={() => setDragOver(null)}
              onDrop={(event) => onDrop(kind, event)}
            >
              <input
                type="file"
                accept={kind === 'png' ? 'image/png,.png' : 'image/svg+xml,.svg'}
                hidden
                onChange={(event) =>
                  assignFile(kind, event.target.files?.[0] || null)
                }
              />
              <span className="upload-drop__badge">{kind.toUpperCase()}</span>
              <span className="upload-drop__title">
                {file ? file.name : `Drop ${kind.toUpperCase()} or browse`}
              </span>
              <span className="upload-drop__hint">Max 2 MB</span>
              {kind === 'png' && pngPreview && (
                <img className="upload-drop__preview" src={pngPreview} alt="" />
              )}
            </label>
          )
        })}
      </div>

      <div className="upload-fields">
        {TEXT_FIELDS.map(([name, label, type, placeholder]) => (
          <label key={name} htmlFor={`${formId}-${name}`}>
            {label}
            {type === 'textarea' ? (
              <textarea
                id={`${formId}-${name}`}
                rows={3}
                value={fields[name]}
                placeholder={placeholder}
                onChange={(event) => updateField(name, event.target.value)}
              />
            ) : (
              <input
                id={`${formId}-${name}`}
                type="text"
                value={fields[name]}
                placeholder={placeholder}
                onChange={(event) => updateField(name, event.target.value)}
              />
            )}
          </label>
        ))}

        <label htmlFor={`${formId}-tags`}>
          Secondary tags
          <input
            id={`${formId}-tags`}
            type="text"
            value={fields.tag_names}
            placeholder="Comma-separated, e.g. park, outdoor"
            onChange={(event) => updateField('tag_names', event.target.value)}
          />
        </label>
      </div>

      {error && (
        <p className="upload-studio__error" role="alert">
          {error}
        </p>
      )}
      {success && (
        <div className="upload-studio__success" role="status">
          <strong>Uploaded.</strong> Icon <code>{success.uniqueId}</code> is{' '}
          <em>{success.status}</em> and waiting for review.
        </div>
      )}

      <button type="submit" className="upload-studio__submit" disabled={submitting}>
        {submitting ? 'Uploading…' : 'Submit icon'}
      </button>
    </form>
  )
}
