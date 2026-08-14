/** Unicode mini chessboard from FEN placement (no engine). */

const PIECES: Record<string, string> = {
  K: "♔",
  Q: "♕",
  R: "♖",
  B: "♗",
  N: "♘",
  P: "♙",
  k: "♚",
  q: "♛",
  r: "♜",
  b: "♝",
  n: "♞",
  p: "♟",
};

function expandFenPlacement(placement: string): (string | null)[][] {
  const ranks = placement.split("/");
  const board: (string | null)[][] = [];
  for (const rank of ranks) {
    const row: (string | null)[] = [];
    for (const ch of rank) {
      if (ch >= "1" && ch <= "8") {
        for (let i = 0; i < Number(ch); i++) row.push(null);
      } else {
        row.push(ch);
      }
    }
    while (row.length < 8) row.push(null);
    board.push(row.slice(0, 8));
  }
  while (board.length < 8) board.push(Array(8).fill(null));
  return board.slice(0, 8);
}

export function MiniBoard({
  fen,
  size = 220,
}: {
  fen: string;
  size?: number;
}) {
  const placement = (fen || "").trim().split(/\s+/)[0] || "8/8/8/8/8/8/8/8";
  const board = expandFenPlacement(placement);
  const cell = size / 8;
  const stm = (fen || "").trim().split(/\s+/)[1] || "?";

  return (
    <div className="inline-block">
      <div
        className="overflow-hidden rounded-lg border border-ink-100 shadow-sm"
        style={{ width: size, height: size }}
        aria-label={`Bàn cờ FEN, bên đi: ${stm}`}
      >
        {board.map((row, r) => (
          <div key={r} className="flex">
            {row.map((piece, c) => {
              const light = (r + c) % 2 === 0;
              return (
                <div
                  key={`${r}-${c}`}
                  className="flex items-center justify-center"
                  style={{
                    width: cell,
                    height: cell,
                    background: light ? "#f0d9b5" : "#b58863",
                    fontSize: cell * 0.72,
                    lineHeight: 1,
                  }}
                >
                  {piece ? PIECES[piece] || piece : ""}
                </div>
              );
            })}
          </div>
        ))}
      </div>
      <p className="mt-1 text-center text-[10px] text-ink-800/60">
        Bên đi: {stm === "w" ? "Trắng" : stm === "b" ? "Đen" : stm}
      </p>
    </div>
  );
}
