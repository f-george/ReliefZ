export default function Panel({ title, children, aside }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-baseline justify-between gap-2">
        <h2 className="text-xs font-semibold tracking-wider text-slate-500 uppercase">{title}</h2>
        {aside}
      </div>
      <div className="space-y-3">{children}</div>
    </section>
  );
}
