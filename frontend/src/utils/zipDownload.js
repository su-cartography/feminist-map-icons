import JSZip from 'jszip'
import { saveFile } from './download'

const META_HEADERS = [
  ['unique_id', 'unique-ID'],
  ['designer', 'designer'],
  ['metadata_source', 'metadata-source'],
  ['uploader', 'uploader'],
  ['primary_tag', 'primary-tags'],
  ['secondary_tags', 'secondary-tags'],
  ['when_created', 'when-created'],
  ['when_uploaded', 'when-uploaded'],
  ['where_created', 'where-created'],
  ['icon_geography', 'icon-geography'],
  ['icon_description', 'icon-description'],
  ['icon_context', 'icon-context'],
  ['creation_context', 'creation-context'],
  ['notes', 'notes'],
]

function csvEscape(value) {
  const text = String(value == null ? '' : value)
  if (/[",\n\r]/.test(text)) return `"${text.replace(/"/g, '""')}"`
  return text
}

function iconMetaValue(icon, key) {
  if (key === 'secondary_tags') {
    return (icon.tags || []).map((tag) => tag.name).filter(Boolean).join(', ')
  }
  return icon[key] ?? ''
}

export function selectedMetadataCsv(icons) {
  const headers = META_HEADERS.map(([, csvKey]) => csvKey)
  const lines = [headers.join(',')]
  icons.forEach((icon) => {
    const row = META_HEADERS.map(([key]) => csvEscape(iconMetaValue(icon, key)))
    lines.push(row.join(','))
  })
  return lines.join('\r\n')
}

export async function downloadPickedZip(icons, kind) {
  if (!icons.length) return

  const out = new JSZip()
  let added = 0

  for (const icon of icons) {
    const url = kind === 'png' ? icon.png_file : icon.svg_file
    if (!url) continue
    const response = await fetch(url)
    if (!response.ok) continue
    const blob = await response.blob()
    out.file(`${icon.unique_id}.${kind}`, blob)
    added += 1
  }

  if (!added) {
    throw new Error(`None of the selected icons had a ${kind.toUpperCase()} file.`)
  }

  out.file('selected-icons-metadata.csv', selectedMetadataCsv(icons))
  const zipBlob = await out.generateAsync({ type: 'blob' })
  await saveFile(zipBlob, `selected-icons-${kind}.zip`)
}
