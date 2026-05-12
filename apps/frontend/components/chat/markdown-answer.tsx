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

export function MarkdownAnswer({ content }: { content: string }) {
  const lines = content.split('\n')
  const blocks: ReactNode[] = []
  let listItems: string[] = []

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

  lines.forEach((line, index) => {
    const trimmed = line.trim()

    if (!trimmed) {
      flushList(`list-${index}`)
      return
    }

    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      listItems.push(trimmed.slice(2))
      return
    }

    flushList(`list-${index}`)

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

  return <div className="prose prose-sm max-w-none text-ops-ink">{blocks}</div>
}
import type { ReactNode } from 'react'
