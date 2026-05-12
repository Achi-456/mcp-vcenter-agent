type ErrorStateProps = {
  title?: string
  message: string
  code?: string | null
}

export function ErrorState({ title = 'Unable to load data', message, code }: ErrorStateProps) {
  return (
    <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-red-800">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-semibold">{title}</h3>
        {code ? <span className="rounded-full bg-white px-2 py-1 text-xs font-semibold">{code}</span> : null}
      </div>
      <p className="mt-2 text-sm leading-6">{message}</p>
    </div>
  )
}
