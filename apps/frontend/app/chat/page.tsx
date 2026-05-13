'use client'

import { Suspense } from 'react'
import { ChatComposer, ChatMessageList, PromptSuggestions } from '@/components/chat'
import { ErrorState, PageHeader, RefreshButton, SectionCard, StatusBadge, ToolBadge } from '@/components/ui'
import { useChatStream } from '@/hooks/use-chat-stream'
import { useSearchParams } from 'next/navigation'

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-ops-muted">Loading chat...</div>}>
      <ChatContent />
    </Suspense>
  )
}

function ChatContent() {
  const searchParams = useSearchParams()
  const initialSessionId = searchParams.get('session_id')
  const { messages, sessionId, isStreaming, isLoadingHistory, streamError, sendMessage, startNewSession } = useChatStream(initialSessionId)
  const toolEvents = messages.flatMap((message) => message.events ?? []).filter((event) => event.type === 'tool_call')
  const blockedEvents = messages.flatMap((message) => message.events ?? []).filter((event) => event.type === 'safety_check' && event.payload.allowed === false)

  return (
    <div className="space-y-6 pb-28">
      <PageHeader
        eyebrow="AI Assistant"
        title="Chat"
        description="Streamed Agent Engine diagnostics with visible intent, safety checks, tool traces, validation, and final answers."
        action={<RefreshButton onRefresh={startNewSession} isRefreshing={false} />}
      />

      <div className="grid gap-5 xl:grid-cols-[1fr_340px]">
        <section className="min-h-[calc(100vh-14rem)] space-y-5">
          <div className="rounded-2xl border border-ops-steel/10 bg-white p-4 shadow-card">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm font-semibold text-ops-ink">Session</p>
                <p className="mt-1 font-mono text-xs text-ops-muted">{sessionId ?? 'New session will be assigned on first stream event.'}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <StatusBadge status={isStreaming ? 'streaming' : isLoadingHistory ? 'loading' : 'ready'} />
                <ToolBadge label={`${toolEvents.length} tool call(s)`} />
                {blockedEvents.length ? <ToolBadge label={`${blockedEvents.length} blocked`} active={false} /> : null}
              </div>
            </div>
          </div>

          {streamError ? <ErrorState title="Chat stream failed" message={streamError} code="STREAM_ERROR" /> : null}

          <div className="max-h-[calc(100vh-18rem)] overflow-y-auto rounded-3xl border border-ops-steel/10 bg-ops-cream/70 p-5">
            {isLoadingHistory ? <p className="mb-4 text-sm text-ops-muted">Loading session history...</p> : null}
            <ChatMessageList messages={messages} />
          </div>
        </section>

        <aside className="space-y-5">
          <SectionCard title="Session Rail" description="Current stream posture.">
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm text-ops-muted">Safety</span>
                <StatusBadge status={blockedEvents.length ? 'blocked seen' : 'ready'} />
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm text-ops-muted">Tool trace</span>
                <ToolBadge label="cards" />
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm text-ops-muted">Raw JSON</span>
                <ToolBadge label="hidden by default" active={false} />
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm text-ops-muted">MCP</span>
                <ToolBadge label="safe status only" />
              </div>
            </div>
          </SectionCard>

          <SectionCard title="Prompt Suggestions">
            <PromptSuggestions onSelect={sendMessage} />
          </SectionCard>
        </aside>
      </div>

      <div className="fixed bottom-0 left-0 right-0 z-30 border-t border-ops-steel/10 bg-ops-cream/95 p-4 backdrop-blur lg:left-72">
        <div className="mx-auto max-w-7xl">
          <ChatComposer disabled={isStreaming || isLoadingHistory} onSend={sendMessage} />
        </div>
      </div>
    </div>
  )
}
