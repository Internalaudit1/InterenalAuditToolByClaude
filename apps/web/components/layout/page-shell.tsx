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
    <div className="min-w-0 space-y-4 lg:space-y-5">
      <section className="panel flex min-w-0 flex-col gap-4 p-4 lg:flex-row lg:items-end lg:justify-between xl:p-5">
        <div className="min-w-0">
          {eyebrow ? <p className="chip">{eyebrow}</p> : null}
          <h1 className="mt-3 break-words font-serif text-3xl leading-tight xl:text-4xl">{title}</h1>
          {description ? <p className="mt-3 max-w-3xl text-sm text-slate">{description}</p> : null}
        </div>
        {actions ? <div className="flex w-full min-w-0 flex-wrap gap-2 lg:w-auto lg:justify-end">{actions}</div> : null}
      </section>
      {children}
    </div>
  );
}
