"use client";

import { CSSProperties, ReactNode, useMemo } from "react";
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable
} from "@tanstack/react-table";

type RowIdentifier = string | number;

type Props<TData> = {
  columns: ColumnDef<TData>[];
  data: TData[];
  enableRowSelection?: boolean;
  selectedRowIds?: RowIdentifier[];
  onSelectedRowIdsChange?: (ids: RowIdentifier[]) => void;
  getRowId?: (row: TData) => RowIdentifier;
  renderRowActions?: (row: TData) => ReactNode;
  bulkActions?: ReactNode;
  maxHeight?: string;
  minTableWidth?: string;
  compactCells?: boolean;
};

function isPrimitiveDisplayValue(value: ReactNode): value is string | number {
  return typeof value === "string" || typeof value === "number";
}

function compactCellStyle(): CSSProperties {
  return {
    display: "-webkit-box",
    WebkitBoxOrient: "vertical",
    WebkitLineClamp: 2,
    overflow: "hidden"
  };
}

export function DataTable<TData>({
  columns,
  data,
  enableRowSelection = false,
  selectedRowIds = [],
  onSelectedRowIdsChange,
  getRowId,
  renderRowActions,
  bulkActions,
  maxHeight = "420px",
  minTableWidth = "1100px",
  compactCells = true
}: Props<TData>) {
  const resolveRowId = (row: TData) => String(getRowId ? getRowId(row) : (row as { id?: RowIdentifier }).id ?? "");
  const selectedSet = new Set(selectedRowIds.map((value) => String(value)));

  const tableColumns = useMemo(() => {
    const computedColumns = [...columns];

    if (enableRowSelection) {
      computedColumns.unshift({
        id: "__select__",
        header: "Select",
        cell: ({ row }) => {
          const rowId = row.id;
          return (
            <input
              type="checkbox"
              checked={selectedSet.has(rowId)}
              onChange={() => {
                if (!onSelectedRowIdsChange) return;
                const next = new Set(selectedSet);
                if (next.has(rowId)) {
                  next.delete(rowId);
                } else {
                  next.add(rowId);
                }
                onSelectedRowIdsChange(Array.from(next));
              }}
            />
          );
        }
      } as ColumnDef<TData>);
    }

    if (renderRowActions) {
      computedColumns.push({
        id: "__actions__",
        header: "Actions",
        cell: ({ row }) => renderRowActions(row.original)
      } as ColumnDef<TData>);
    }

    return computedColumns;
  }, [columns, enableRowSelection, onSelectedRowIdsChange, renderRowActions, selectedSet]);

  const table = useReactTable({
    data,
    columns: tableColumns,
    getCoreRowModel: getCoreRowModel(),
    getRowId: (originalRow) => resolveRowId(originalRow)
  });

  const visibleRowIds = table.getRowModel().rows.map((row) => row.id);
  const allVisibleSelected = visibleRowIds.length > 0 && visibleRowIds.every((rowId) => selectedSet.has(rowId));
  const shouldUseFixedScrollArea = data.length > 8;

  return (
    <div className="panel overflow-hidden">
      {bulkActions ? <div className="border-b border-sand/60 px-4 py-3">{bulkActions}</div> : null}
      <div
        className="relative overflow-auto"
        style={{
          height: shouldUseFixedScrollArea ? maxHeight : undefined,
          maxHeight
        }}
      >
        <table className="w-full text-sm" style={{ minWidth: minTableWidth }}>
          <thead className="bg-sand/60 text-left text-xs uppercase tracking-[0.16em] text-slate">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th key={header.id} className="sticky top-0 z-10 bg-sand px-4 py-3 font-semibold">
                    {header.isPlaceholder ? null : header.column.id === "__select__" ? (
                      <input
                        type="checkbox"
                        checked={allVisibleSelected}
                        onChange={() => {
                          if (!onSelectedRowIdsChange) return;
                          if (allVisibleSelected) {
                            const remaining = selectedRowIds.filter((id) => !visibleRowIds.includes(String(id)));
                            onSelectedRowIdsChange(remaining);
                            return;
                          }
                          const next = new Set(selectedSet);
                          visibleRowIds.forEach((rowId) => next.add(rowId));
                          onSelectedRowIdsChange(Array.from(next));
                        }}
                      />
                    ) : flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="border-t border-sand/50 bg-white/70">
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-4 py-3 align-top">
                    {(() => {
                      const rendered = flexRender(cell.column.columnDef.cell, cell.getContext());
                      const shouldClamp = compactCells && cell.column.id !== "__select__" && cell.column.id !== "__actions__" && isPrimitiveDisplayValue(rendered);

                      return shouldClamp ? (
                        <div className="max-w-96 whitespace-normal break-words" style={compactCellStyle()} title={String(rendered)}>
                          {rendered}
                        </div>
                      ) : rendered;
                    })()}
                  </td>
                ))}
              </tr>
            ))}
            {!table.getRowModel().rows.length ? (
              <tr>
                <td colSpan={tableColumns.length} className="px-4 py-10 text-center text-slate">
                  No data available.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
