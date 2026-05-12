import type { ReactNode } from 'react'

function inlineMarkdown(text: string) {
  const segments = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g)

  return segments.map((segment, index) => {
    if (segment.startsWith('`') && segment.endsWith('`')) {
      return (
        <code key={index} className="rounded bg-ops-cream px-1.5 py-0.5 font-mono text-xs text-ops-navy">
          {segment.slice(1, -1)}
        </code>
      )
    }

    if (segment.startsWith('**') && segment.endsWith('**')) {
      return (
        <strong key={index} className="font-semibold text-ops-ink">
          {segment.slice(2, -2)}
        </strong>
      )
    }

    return <span key={index}>{segment}</span>
  })
}

function isTableSeparator(line: string) {
  return /^\|?[\s:-]+\|[\s|:-]+$/.test(line)
}

function parseTableRow(line: string) {
  return line
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim())
}

export function MarkdownAnswer({ content }: { content: string }) {
  const lines = content.split('\n')
  const blocks: ReactNode[] = []
  let listItems: string[] = []
  let tableRows: string[][] = []

  function flushList(key: string) {
    if (!listItems.length) return
    blocks.push(
      <ul key={key} className="my-3 list-disc space-y-1 pl-5">
        {listItems.map((item, index) => (
          <li key={`${key}-${index}`}>{inlineMarkdown(item)}</li>
        ))}
      </ul>,
    )
    listItems = []
  }

  function flushTable(key: string) {
    if (!tableRows.length) return
    const [header, ...rows] = tableRows

    blocks.push(
      <div key={key} className="my-4 overflow-x-auto rounded-xl border border-ops-steel/10">
        <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
          <thead className="bg-ops-cream">
            <tr>
              {header.map((cell, index) => (
                <th key={`${key}-head-${index}`} className="border-b border-ops-steel/10 px-3 py-2 font-semibold text-ops-ink">
                  {inlineMarkdown(cell)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={`${key}-row-${rowIndex}`}>
                {row.map((cell, cellIndex) => (
                  <td key={`${key}-cell-${rowIndex}-${cellIndex}`} className="border-b border-ops-steel/10 px-3 py-2 text-ops-muted">
                    {inlineMarkdown(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>,
    )
    tableRows = []
  }

  lines.forEach((line, index) => {
    const trimmed = line.trim()

    if (!trimmed) {
      flushList(`list-${index}`)
      flushTable(`table-${index}`)
      return
    }

    if (isTableSeparator(trimmed)) {
      return
    }

    if (trimmed.includes('|')) {
      flushList(`list-${index}`)
      tableRows.push(parseTableRow(trimmed))
      return
    }

    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      flushTable(`table-${index}`)
      listItems.push(trimmed.slice(2))
      return
    }

    flushList(`list-${index}`)
    flushTable(`table-${index}`)

    if (trimmed.startsWith('### ')) {
      blocks.push(
        <h3 key={index} className="mb-2 mt-4 text-base font-semibold text-ops-ink">
          {inlineMarkdown(trimmed.slice(4))}
        </h3>,
      )
      return
    }

    if (trimmed.startsWith('## ')) {
      blocks.push(
        <h2 key={index} className="mb-2 mt-4 text-lg font-semibold text-ops-ink">
          {inlineMarkdown(trimmed.slice(3))}
        </h2>,
      )
      return
    }

    if (trimmed.startsWith('# ')) {
      blocks.push(
        <h1 key={index} className="mb-2 mt-4 text-xl font-semibold text-ops-ink">
          {inlineMarkdown(trimmed.slice(2))}
        </h1>,
      )
      return
    }

    blocks.push(
      <p key={index} className="my-2 leading-7">
        {inlineMarkdown(trimmed)}
      </p>,
    )
  })

  flushList('list-final')
  flushTable('table-final')

  return <div className="max-w-none text-sm leading-7 text-ops-ink">{blocks}</div>
}
