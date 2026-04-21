import { motion } from "framer-motion";
import { hasConflict, pairConflictH, pairConflictV } from "../utils/puzzle";

export default function Board({
  puzzle,
  grid,
  selected,
  onCellClick,
  celebrateTick = 0,
  celebrateActive = false,
  loadTick = 0,
  loadActive = false
}) {
  if (!puzzle || !grid) return <div className="boardEmpty">Load a puzzle input to begin.</div>;
  const n = puzzle.n;
  const trackSize = n >= 9 ? 30 : n >= 7 ? 36 : 48;
  const boardGap = n >= 9 ? 4 : n >= 7 ? 5 : 6;

  // Exactly one animation can run at a time, deterministic priority:
  // 1) celebration (victory)  2) load animation  3) none
  const run = celebrateActive
    ? { mode: "celebrate", tick: celebrateTick }
    : loadActive
      ? { mode: "load", tick: loadTick }
      : null;

  const rows = [];
  for (let i = 0; i < n; i += 1) {
    for (let j = 0; j < n; j += 1) {
      const v = grid[i][j];
      const clue = puzzle.grid[i][j] !== 0;
      const conflict = v !== 0 && hasConflict(puzzle, grid, i, j, v);
      const delayIndex =
        run?.mode === "celebrate"
          ? (n - 1 - i) * n + (n - 1 - j) // bottom->top, right->left
          : run?.mode === "load"
            ? i * n + (n - 1 - j) // top->bottom, right->left
            : 0;
      const delayStep = run?.mode === "celebrate" ? 0.024 : run?.mode === "load" ? 0.018 : 0;
      rows.push(
        <motion.button
          key={`c-${i}-${j}-${run ? `${run.mode}-${run.tick}` : "idle"}`}
          className={`cell ${clue ? "clue" : ""} ${conflict ? "conflict" : ""} ${selected?.[0] === i && selected?.[1] === j ? "selected" : ""}`}
          onClick={() => onCellClick(i, j)}
          disabled={clue}
          whileTap={clue ? undefined : { scale: 0.972 }}
          initial={{ y: 0, scale: 1 }}
          animate={
            run
              ? { y: [0, -14, 0], scale: [1, 1.16, 1] }
              : { y: 0, scale: 1 }
          }
          transition={{
            duration: run?.mode === "celebrate" ? 0.38 : 0.32,
            ease: [0.2, 0.85, 0.24, 1],
            delay: run ? delayIndex * delayStep : 0
          }}
        >
          {v === 0 ? "" : v}
        </motion.button>
      );
      if (j < n - 1) {
        const rel = puzzle.hcons[i][j];
        const leftClue = puzzle.grid[i][j] !== 0;
        const rightClue = puzzle.grid[i][j + 1] !== 0;
        const showRel = !(leftClue || rightClue);
        rows.push(
          <div key={`h-${i}-${j}`} className={`ineq h ${pairConflictH(puzzle, grid, i, j) ? "bad" : ""}`}>
            {showRel ? (rel === 1 ? "<" : rel === -1 ? ">" : "") : ""}
          </div>
        );
      }
    }
    if (i < n - 1) {
      for (let j = 0; j < n; j += 1) {
        const rel = puzzle.vcons[i][j];
        const topClue = puzzle.grid[i][j] !== 0;
        const bottomClue = puzzle.grid[i + 1][j] !== 0;
        const showRel = !(topClue || bottomClue);
        rows.push(
          <div key={`v-${i}-${j}`} className={`ineq v ${pairConflictV(puzzle, grid, i, j) ? "bad" : ""}`}>
            {showRel ? (rel === 1 ? "^" : rel === -1 ? "v" : "") : ""}
          </div>
        );
        if (j < n - 1) rows.push(<div key={`sp-${i}-${j}`} className="ineqSpacer" />);
      }
    }
  }
  return (
    <div
      className="boardGrid"
      style={{
        gridTemplateColumns: `repeat(${n * 2 - 1}, ${trackSize}px)`,
        gap: `${boardGap}px`
      }}
    >
      {rows}
    </div>
  );
}
