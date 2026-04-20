export function PageShell({
  title,
  eyebrow,
  description,
  actions,
  children
}: {
  title: string;
  eyebrow?: string;
  description?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-6">
      <section className="panel flex flex-col gap-4 p-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          {eyebrow ? <p className="chip">{eyebrow}</p> : null}
          <h1 className="mt-3 font-serif text-4xl">{title}</h1>
          {description ? <p className="mt-3 max-w-3xl text-sm text-slate">{description}</p> : null}
        </div>
        {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}
      </section>
      {children}
    </div>
  );
}

