import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import Board from "./components/Board";
import GlassButton from "./components/GlassButton";
import { ALGOS, API_BASE } from "./constants";
import { cloneGrid, isSolvedGrid, parseName } from "./utils/puzzle";

function Stat({ label, value }) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function formatTraceEvent(step, idx) {
  if (!Array.isArray(step) || step.length < 4) {
    return `${idx + 1}. TRACE EVENT`;
  }
  const [action, i, j, v] = step;
  if (action === "fallback") {
    const unresolved = Number.isFinite(v) && v >= 0 ? v : 0;
    return `${idx + 1}. FALLBACK: Forward fixpoint reached, switch to backtracking with ${unresolved} unresolved cells`;
  }
  const label = String(action || "").toUpperCase();
  const valueText = action === "unset" ? "∅" : `${v}`;
  return `${idx + 1}. ${label} @ (${i + 1},${j + 1}) = ${valueText}`;
}

export default function App() {
  const [algo, setAlgo] = useState("astar");
  const [sourceName, setSourceName] = useState("—");
  const [rawInput, setRawInput] = useState("");
  const [puzzle, setPuzzle] = useState(null);
  const [grid, setGrid] = useState(null);
  const [solvedGrid, setSolvedGrid] = useState(null);
  const [trace, setTrace] = useState([]);
  const [log, setLog] = useState([]);
  const [metrics, setMetrics] = useState({
    runtime: "—",
    nodes: "—",
    memory: "—",
    steps: "—",
    solutionSteps: "—"
  });
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [inputFiles, setInputFiles] = useState([]);
  const [pickedInput, setPickedInput] = useState("");
  const [isReplaying, setIsReplaying] = useState(false);
  const [replayIndex, setReplayIndex] = useState(0);
  const [replayMs, setReplayMs] = useState(45);
  const [celebrateTick, setCelebrateTick] = useState(0);
  const [celebrateActive, setCelebrateActive] = useState(false);
  const [loadTick, setLoadTick] = useState(0);
  const [loadActive, setLoadActive] = useState(false);
  const replayDeadlineRef = useRef(0);
  const replayLastProgressRef = useRef(0);
  const wasSolvedRef = useRef(false);

  const n = puzzle?.n ?? 0;
  const total = n * n;
  const filled = useMemo(() => {
    if (!grid || !n) return 0;
    return grid.flat().filter((v) => v !== 0).length;
  }, [grid, n]);
  const boardSolved = useMemo(() => isSolvedGrid(puzzle, grid), [puzzle, grid]);

  const appendLog = (line) => setLog((prev) => [...prev, line]);

  useEffect(() => {
    fetch(`${API_BASE}/api/inputs`)
      .then((r) => r.json())
      .then((data) => {
        const files = data.files || [];
        setInputFiles(files);
        if (files.length) setPickedInput(files[0]);
      })
      .catch(() => {
        // no-op: user can still paste/upload input manually
      });
  }, []);

  const replayActions = useMemo(() => {
    const base = trace.filter((step) => ["set", "propagate", "commit", "unset", "fallback"].includes(step?.[0]));
    if (!puzzle || !solvedGrid) return base;

    // Build a deterministic "complete replay": raw trace + synthetic reveals
    // for any cells still not matching solved_grid after trace application.
    const sim = cloneGrid(puzzle.grid);
    for (const step of base) {
      const [action, i, j, v] = step;
      if (!["set", "propagate", "commit", "unset", "reveal"].includes(action)) continue;
      if (action === "unset") sim[i][j] = 0;
      else sim[i][j] = v;
    }

    const reveal = [];
    for (let i = 0; i < puzzle.n; i += 1) {
      for (let j = 0; j < puzzle.n; j += 1) {
        if (sim[i][j] !== solvedGrid[i][j]) {
          reveal.push(["reveal", i, j, solvedGrid[i][j]]);
        }
      }
    }
    return [...base, ...reveal];
  }, [trace, puzzle, solvedGrid]);

  useEffect(() => {
    setMetrics((prev) => ({
      ...prev,
      steps: replayActions.length ? `${replayActions.length}` : "—"
    }));
  }, [replayActions]);

  useEffect(() => {
    if (!boardSolved) {
      wasSolvedRef.current = false;
      setCelebrateActive(false);
      return;
    }
    if (wasSolvedRef.current) return;
    wasSolvedRef.current = true;
    setCelebrateTick((tick) => tick + 1);
    setCelebrateActive(true);
    appendLog("✨ Board complete");
  }, [boardSolved]);

  useEffect(() => {
    if (!celebrateTick) return undefined;
    const nLocal = puzzle?.n ?? 9;
    const totalMs = 380 + (nLocal * nLocal) * 24 + 200; // duration + cascade + buffer
    const id = setTimeout(() => setCelebrateActive(false), totalMs);
    return () => clearTimeout(id);
  }, [celebrateTick, puzzle?.n]);

  useEffect(() => {
    if (!loadTick) return undefined;
    const nLocal = puzzle?.n ?? 9;
    const totalMs = 360 + (nLocal * nLocal) * 18 + 200;
    const id = setTimeout(() => setLoadActive(false), totalMs);
    return () => clearTimeout(id);
  }, [loadTick, puzzle?.n]);

  const parseInputText = async (content, nameHint = "manual-input.txt") => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/puzzle/parse`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content })
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Parse failed");
      const data = await res.json();
      setPuzzle(data.puzzle);
      setGrid(cloneGrid(data.puzzle.grid));
      setSolvedGrid(null);
      setTrace([]);
      setSourceName(parseName(nameHint));
      setMetrics({ runtime: "—", nodes: "—", memory: "—", steps: "—", solutionSteps: "—" });
      setLog([`✦ Loaded n=${data.puzzle.n} (${parseName(nameHint)})`]);
      setSelected(null);
      wasSolvedRef.current = false;
      setCelebrateActive(false);
      setLoadActive(true);
      setLoadTick((t) => t + 1);
    } catch (e) {
      appendLog(`✗ Parse error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const onFile = async (ev) => {
    const f = ev.target.files?.[0];
    if (!f) return;
    const text = await f.text();
    setRawInput(text);
    await parseInputText(text, f.name);
  };

  const cycleCell = (i, j) => {
    if (!puzzle || !grid) return;
    if (puzzle.grid[i][j] !== 0) return;
    const next = cloneGrid(grid);
    next[i][j] = (next[i][j] + 1) % (puzzle.n + 1);
    setGrid(next);
    setSelected([i, j]);
  };

  const runSolve = async () => {
    if (!puzzle) return;
    setLoading(true);
    // Prevent stale success state from previous runs.
    setSolvedGrid(null);
    setTrace([]);
    setReplayIndex(0);
    setIsReplaying(false);
    setGrid(cloneGrid(puzzle.grid));
    try {
      appendLog(`⚙ Running: ${algo} ...`);
      const res = await fetch(`${API_BASE}/api/solve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ algo, puzzle })
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Solve failed");
      const data = await res.json();
      if (data.solved_grid) {
        setSolvedGrid(data.solved_grid);
        setGrid(cloneGrid(data.solved_grid));
      }
      setTrace(data.trace || []);
      setReplayIndex(0);
      setIsReplaying(false);
      for (const line of data.messages || []) appendLog(`  ${line}`);
      setMetrics({
        runtime: `${(data.runtime_sec || 0).toFixed(4)}s`,
        nodes: `${data.nodes_expanded ?? "—"}`,
        memory: `${Math.round((data.memory_kb ?? 0) * 1024)} B`,
        steps: `${replayActions.length || (data.trace || []).length || 0}`,
        solutionSteps: `${(data.trace || []).length || 0}`
      });
      if (!data.solved_grid || data.contradiction) appendLog("✗ No solution found.");
      else appendLog("✓ Solved.");
    } catch (e) {
      appendLog(`✗ Solve error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadSampleInput = async () => {
    if (!pickedInput) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/inputs/${encodeURIComponent(pickedInput)}`);
      if (!res.ok) throw new Error((await res.json()).detail || "Load sample failed");
      const data = await res.json();
      setRawInput(data.content);
      await parseInputText(data.content, data.name);
    } catch (e) {
      appendLog(`✗ Sample load error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const stopReplay = () => {
    setIsReplaying(false);
  };

  const applyTraceEvent = (event) => {
    if (!puzzle) return;
    const [action, i, j, v] = event;
    if (!["set", "propagate", "commit", "unset", "reveal"].includes(action)) return;
    setGrid((prev) => {
      if (!prev) return prev;
      const next = cloneGrid(prev);
      next[i][j] = action === "unset" ? 0 : v;
      return next;
    });
    setSelected([i, j]);
  };

  const startReplay = () => {
    if (!puzzle || !replayActions.length) return;
    replayDeadlineRef.current = Date.now() + 300_000; // 300s hard timeout
    replayLastProgressRef.current = Date.now();
    if (replayIndex === 0) {
      setGrid(cloneGrid(puzzle.grid));
      setLog((prev) => [...prev, `▶ Replay started (${replayActions.length} steps, timeout 300s)`]);
    }
    setIsReplaying(true);
  };

  useEffect(() => {
    if (!isReplaying) return undefined;
    if (Date.now() >= replayDeadlineRef.current) {
      setIsReplaying(false);
      setLog((prev) => [...prev, "⏱ Replay stopped after 300s timeout."]);
      return undefined;
    }
    if (replayIndex >= replayActions.length) {
      setIsReplaying(false);
      setLog((prev) => [...prev, "■ Replay complete"]);
      return undefined;
    }
    const id = setTimeout(() => {
      if (Date.now() >= replayDeadlineRef.current) {
        setIsReplaying(false);
        setLog((prev) => [...prev, "⏱ Replay stopped after 300s timeout."]);
        return;
      }
      applyTraceEvent(replayActions[replayIndex]);
      replayLastProgressRef.current = Date.now();
      setReplayIndex((idx) => idx + 1);
    }, replayMs);
    return () => clearTimeout(id);
  }, [isReplaying, replayIndex, replayActions, replayMs]); // deterministic step replay

  // Watchdog: if replay stalls unexpectedly, force progress.
  useEffect(() => {
    if (!isReplaying) return undefined;
    const id = setInterval(() => {
      if (!isReplaying) return;
      if (Date.now() >= replayDeadlineRef.current) return;
      if (replayIndex >= replayActions.length) return;
      const stallThreshold = Math.max(1200, replayMs * 8);
      if (Date.now() - replayLastProgressRef.current < stallThreshold) return;
      applyTraceEvent(replayActions[replayIndex]);
      replayLastProgressRef.current = Date.now();
      setReplayIndex((idx) => idx + 1);
    }, 400);
    return () => clearInterval(id);
  }, [isReplaying, replayIndex, replayActions, replayMs]);

  const saveOutput = async () => {
    if (!puzzle || !solvedGrid) return;
    const res = await fetch(`${API_BASE}/api/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ puzzle, solved: solvedGrid })
    });
    if (!res.ok) {
      appendLog("✗ Export failed.");
      return;
    }
    const data = await res.json();
    const blob = new Blob([data.text], { type: "text/plain;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "solution.txt";
    a.click();
    URL.revokeObjectURL(a.href);
    appendLog("✓ Saved solution.txt");
  };

  return (
    <div className="page">
      <div className="mesh" />
      <header className="titleGlass">
        <h1>Futoshiki</h1>
      </header>

      <main className="layout">
        <section className="glass panel interactive boardPanel">
          <div className="boardHeader">
            <strong>Board</strong>
            <span>
              {filled}/{total || "—"}
            </span>
          </div>
          <Board
            puzzle={puzzle}
            grid={grid}
            selected={selected}
            onCellClick={cycleCell}
            celebrateTick={celebrateTick}
            celebrateActive={celebrateActive}
            loadTick={loadTick}
            loadActive={loadActive}
          />
          <p className="legend">Blue: clue · Light: solved · Red: conflict</p>
        </section>

        <section className="glass panel interactive controlPanel">
          <label className="label">Algorithm</label>
          <div className="algoList">
            {ALGOS.map(([key, name]) => (
              <motion.button
                key={key}
                className={`chip ${algo === key ? "active" : ""}`}
                onClick={() => setAlgo(key)}
                whileTap={{ scale: 0.95, y: 1 }}
                transition={{ type: "spring", stiffness: 420, damping: 24, mass: 0.66 }}
              >
                {name}
              </motion.button>
            ))}
          </div>

          <label className="label">Test input (from folder inputs)</label>
          <div className="sampleRow">
            <select value={pickedInput} onChange={(e) => setPickedInput(e.target.value)}>
              {inputFiles.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
            <GlassButton onClick={loadSampleInput} disabled={loading || !pickedInput}>
              Load test
            </GlassButton>
          </div>

          <label className="label">Load input (.txt)</label>
          <input type="file" accept=".txt" onChange={onFile} />

          <label className="label">Or paste input</label>
          <textarea
            className="inputBox"
            value={rawInput}
            onChange={(e) => setRawInput(e.target.value)}
            placeholder="Paste puzzle text here..."
          />

          <div className="btnRow">
            <GlassButton onClick={() => parseInputText(rawInput)} disabled={loading || !rawInput.trim()}>
              Parse
            </GlassButton>
            <GlassButton onClick={runSolve} disabled={loading || !puzzle}>
              Solve
            </GlassButton>
            <GlassButton onClick={saveOutput} disabled={!solvedGrid}>
              Save
            </GlassButton>
          </div>

          <label className="label">Trace replay</label>
          <div className="replayRow">
            <GlassButton onClick={startReplay} disabled={!replayActions.length || isReplaying}>
              Replay
            </GlassButton>
            <GlassButton onClick={stopReplay} disabled={!isReplaying}>
              Pause
            </GlassButton>
          </div>
          <div className="speedRow">
            <span>Speed</span>
            <input type="range" min="12" max="220" step="4" value={replayMs} onChange={(e) => setReplayMs(Number(e.target.value))} />
            <span>{replayMs}ms</span>
          </div>

          <div className="source">Input: {sourceName}</div>
        </section>

        <section className="glass panel interactive rightPanel">
          <div className="metrics">
            <Stat label="Execution Time" value={metrics.runtime} />
            <Stat label="Nodes Expanded" value={metrics.nodes} />
            <Stat label="Memory Usage" value={metrics.memory} />
            <Stat label="Solution Steps" value={metrics.solutionSteps} />
            <Stat label="Trace Steps" value={metrics.steps} />
          </div>

          <h3>Trace / Logs</h3>
          <div className="logBox">
            <AnimatePresence initial={false}>
              {log.map((line, idx) => (
                <motion.div
                  key={`${idx}-${line.slice(0, 10)}`}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  {line}
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
          <h3>Trace Steps</h3>
          <div className="traceBox">
            {replayActions.length === 0 ? (
              <div className="traceEmpty">No trace yet. Run Solve first.</div>
            ) : (
              replayActions.map((step, idx) => (
                <div key={`t-${idx}`} className={`traceRow ${idx === replayIndex - 1 ? "active" : ""}`}>
                  {formatTraceEvent(step, idx)}
                </div>
              ))
            )}
          </div>
          <small>Trace events: {replayActions.length}</small>
        </section>
      </main>
    </div>
  );
}
