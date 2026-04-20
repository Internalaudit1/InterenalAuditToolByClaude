export function StatGrid({ items }: { items: { label: string; value: number | string; hint?: string }[] }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {items.map((item) => (
        <div key={item.label} className="panel p-5">
          <p className="text-xs uppercase tracking-[0.18em] text-slate">{item.label}</p>
          <div className="mt-3 text-4xl font-semibold">{item.value}</div>
          {item.hint ? <p className="mt-2 text-sm text-slate">{item.hint}</p> : null}
        </div>
      ))}
    </div>
  );
}

