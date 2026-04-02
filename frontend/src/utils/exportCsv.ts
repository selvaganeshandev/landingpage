/**
 * Utility to export data as a CSV file download
 */

export function downloadCsv(
  rows: Record<string, string | number>[],
  headers: { key: string; label: string }[],
  filename: string
) {
  if (!rows.length) return;

  const headerLine = headers.map(h => `"${h.label}"`).join(',');
  const dataLines = rows.map(row =>
    headers
      .map(h => {
        const val = row[h.key] ?? '';
        // Escape double-quotes inside values
        return `"${String(val).replace(/"/g, '""')}"`;
      })
      .join(',')
  );

  const csv = [headerLine, ...dataLines].join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
