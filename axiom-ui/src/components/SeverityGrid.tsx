import type { FmeaEntry } from '../types/api';

interface SeverityGridProps {
  entries: FmeaEntry[];
}

function rpnColor(rpn: number): string {
  if (rpn >= 200) return 'bg-red-600 text-white';
  if (rpn >= 100) return 'bg-orange-500 text-white';
  if (rpn >= 50) return 'bg-yellow-400 text-gray-900';
  return 'bg-green-400 text-gray-900';
}

export function SeverityGrid({ entries }: SeverityGridProps) {
  if (entries.length === 0) {
    return (
      <p className="text-gray-400 italic" data-testid="severity-grid-empty">
        No FMEA data available
      </p>
    );
  }

  // Build a 5x5 grid: severity (y-axis, 5→1) × occurrence (x-axis, 1→5)
  const grid: FmeaEntry[][][] = Array.from({ length: 5 }, () =>
    Array.from({ length: 5 }, () => []),
  );

  for (const entry of entries) {
    const row = Math.min(Math.max(entry.severity, 1), 5) - 1;
    const col = Math.min(Math.max(entry.occurrence, 1), 5) - 1;
    grid[row][col].push(entry);
  }

  return (
    <div data-testid="severity-grid">
      <div className="overflow-x-auto">
        <table className="border-collapse text-xs w-full">
          <thead>
            <tr>
              <th className="p-1 border text-center">S \ O</th>
              {[1, 2, 3, 4, 5].map((o) => (
                <th key={o} className="p-1 border text-center">
                  {o}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[5, 4, 3, 2, 1].map((sev) => (
              <tr key={sev}>
                <td className="p-1 border text-center font-semibold">{sev}</td>
                {[1, 2, 3, 4, 5].map((occ) => {
                  const cell = grid[sev - 1][occ - 1];
                  const maxRpn = cell.length
                    ? Math.max(...cell.map((e) => e.rpn))
                    : 0;
                  return (
                    <td
                      key={occ}
                      className={`p-1 border text-center min-w-[40px] ${cell.length ? rpnColor(maxRpn) : ''}`}
                      data-testid={`cell-${sev}-${occ}`}
                      title={cell.map((e) => `${e.id}: RPN ${e.rpn}`).join(', ')}
                    >
                      {cell.length > 0 && (
                        <span>{cell.map((e) => e.id).join(', ')}</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend table */}
      <div className="mt-4 overflow-x-auto">
        <table className="text-xs border-collapse w-full">
          <thead>
            <tr>
              <th className="p-1 border">ID</th>
              <th className="p-1 border">Failure Mode</th>
              <th className="p-1 border">Component</th>
              <th className="p-1 border">S</th>
              <th className="p-1 border">O</th>
              <th className="p-1 border">D</th>
              <th className="p-1 border">RPN</th>
              <th className="p-1 border">Action</th>
            </tr>
          </thead>
          <tbody>
            {entries
              .sort((a, b) => b.rpn - a.rpn)
              .map((e) => (
                <tr key={e.id}>
                  <td className="p-1 border font-mono">{e.id}</td>
                  <td className="p-1 border">{e.failure_mode}</td>
                  <td className="p-1 border">{e.component}</td>
                  <td className="p-1 border text-center">{e.severity}</td>
                  <td className="p-1 border text-center">{e.occurrence}</td>
                  <td className="p-1 border text-center">{e.detection}</td>
                  <td className={`p-1 border text-center font-bold ${rpnColor(e.rpn)}`}>
                    {e.rpn}
                  </td>
                  <td className="p-1 border">{e.recommended_action}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
