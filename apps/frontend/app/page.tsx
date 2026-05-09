const cards = [
  ['API Gateway', 'Ready baseline', 'FastAPI health and SSE placeholder'],
  ['Agent Engine', 'Rebuild target', 'Worker-02 LangGraph service comes next'],
  ['MCP Server', 'Placeholder', 'Tools/resources/prompts currently empty'],
  ['GitOps', 'Preserved', 'Argo CD manifests stay in k8s/ for later adoption'],
]

export default function Home() {
  return (
    <main className="grid-shell min-h-screen px-6 py-8">
      <section className="mx-auto flex max-w-6xl flex-col gap-8">
        <div className="rounded-3xl border border-emerald-400/20 bg-black/35 p-8 shadow-2xl shadow-emerald-500/10 backdrop-blur">
          <p className="text-sm uppercase tracking-[0.45em] text-emerald-300/80">
            vCenter Agentic Ops
          </p>
          <h1 className="mt-4 max-w-3xl text-4xl font-semibold tracking-tight text-white md:text-6xl">
            Clean rebuild baseline for the infrastructure agent console.
          </h1>
          <p className="mt-5 max-w-2xl text-lg text-emerald-50/70">
            This branch intentionally resets the broken app layer to a small,
            verifiable foundation: UI shell, FastAPI gateway, agent-engine
            placeholder, and MCP placeholder.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a
              href="/chat"
              className="rounded-full bg-emerald-400 px-5 py-3 text-sm font-semibold text-black transition hover:bg-emerald-300"
            >
              Open chat
            </a>
            <a
              href="/api/health"
              className="rounded-full border border-emerald-300/30 px-5 py-3 text-sm font-semibold text-emerald-100 transition hover:border-emerald-200"
            >
              Check UI health
            </a>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {cards.map(([title, status, detail]) => (
            <article
              key={title}
              className="rounded-2xl border border-emerald-400/15 bg-console-panel/80 p-5 backdrop-blur"
            >
              <div className="flex items-center justify-between gap-4">
                <h2 className="text-xl font-semibold text-white">{title}</h2>
                <span className="rounded-full border border-emerald-300/30 px-3 py-1 text-xs text-emerald-200">
                  {status}
                </span>
              </div>
              <p className="mt-3 text-sm text-emerald-50/65">{detail}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  )
}

