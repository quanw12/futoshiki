export function cloneGrid(grid) {
  return grid.map((r) => [...r]);
}

export function parseName(fileName) {
  const i = Math.max(fileName.lastIndexOf("/"), fileName.lastIndexOf("\\"));
  return i >= 0 ? fileName.slice(i + 1) : fileName;
}

function relationOk(a, b, rel) {
  if (a === 0 || b === 0 || rel === 0) return true;
  if (rel === 1) return a < b;
  if (rel === -1) return a > b;
  return true;
}

export function hasConflict(puzzle, grid, i, j, v) {
  if (!puzzle || v === 0) return false;
  const n = puzzle.n;
  for (let jj = 0; jj < n; jj += 1) if (jj !== j && grid[i][jj] === v) return true;
  for (let ii = 0; ii < n; ii += 1) if (ii !== i && grid[ii][j] === v) return true;
  if (j < n - 1 && !relationOk(v, grid[i][j + 1], puzzle.hcons[i][j])) return true;
  if (j > 0 && !relationOk(grid[i][j - 1], v, puzzle.hcons[i][j - 1])) return true;
  if (i < n - 1 && !relationOk(v, grid[i + 1][j], puzzle.vcons[i][j])) return true;
  if (i > 0 && !relationOk(grid[i - 1][j], v, puzzle.vcons[i - 1][j])) return true;
  return false;
}

export function pairConflictH(puzzle, grid, i, j) {
  if (!puzzle) return false;
  const rel = puzzle.hcons[i][j];
  if (!rel) return false;
  const a = grid[i][j];
  const b = grid[i][j + 1];
  if (a && b && !relationOk(a, b, rel)) return true;
  return (a && hasConflict(puzzle, grid, i, j, a)) || (b && hasConflict(puzzle, grid, i, j + 1, b));
}

export function pairConflictV(puzzle, grid, i, j) {
  if (!puzzle) return false;
  const rel = puzzle.vcons[i][j];
  if (!rel) return false;
  const a = grid[i][j];
  const b = grid[i + 1][j];
  if (a && b && !relationOk(a, b, rel)) return true;
  return (a && hasConflict(puzzle, grid, i, j, a)) || (b && hasConflict(puzzle, grid, i + 1, j, b));
}

export function isSolvedGrid(puzzle, grid) {
  if (!puzzle || !grid) return false;
  const n = puzzle.n;
  if (grid.length !== n || grid.some((row) => row.length !== n)) return false;

  for (let i = 0; i < n; i += 1) {
    const rowSet = new Set();
    for (let j = 0; j < n; j += 1) {
      const v = grid[i][j];
      if (!Number.isInteger(v) || v < 1 || v > n) return false;
      if (rowSet.has(v)) return false;
      rowSet.add(v);
    }
  }

  for (let j = 0; j < n; j += 1) {
    const colSet = new Set();
    for (let i = 0; i < n; i += 1) {
      const v = grid[i][j];
      if (colSet.has(v)) return false;
      colSet.add(v);
    }
  }

  for (let i = 0; i < n; i += 1) {
    for (let j = 0; j < n - 1; j += 1) {
      if (!relationOk(grid[i][j], grid[i][j + 1], puzzle.hcons[i][j])) return false;
    }
  }

  for (let i = 0; i < n - 1; i += 1) {
    for (let j = 0; j < n; j += 1) {
      if (!relationOk(grid[i][j], grid[i + 1][j], puzzle.vcons[i][j])) return false;
    }
  }

  return true;
}
