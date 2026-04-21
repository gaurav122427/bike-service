import { useState } from "react";

const BTN = "flex items-center justify-center h-11 rounded-xl text-sm font-semibold transition-all active:scale-95 select-none cursor-pointer";

export default function Calculator() {
  const [open, setOpen] = useState(false);
  const [display, setDisplay] = useState("0");
  const [prev, setPrev] = useState(null);
  const [op, setOp] = useState(null);
  const [waitNext, setWaitNext] = useState(false);

  const pressDigit = (d) => {
    if (waitNext) {
      setDisplay(String(d));
      setWaitNext(false);
    } else {
      setDisplay(display === "0" ? String(d) : display + d);
    }
  };

  const pressDot = () => {
    if (waitNext) { setDisplay("0."); setWaitNext(false); return; }
    if (!display.includes(".")) setDisplay(display + ".");
  };

  const pressOp = (o) => {
    const cur = parseFloat(display);
    if (prev !== null && !waitNext) {
      const result = calc(prev, cur, op);
      setDisplay(fmt(result));
      setPrev(result);
    } else {
      setPrev(cur);
    }
    setOp(o);
    setWaitNext(true);
  };

  const calc = (a, b, o) => {
    if (o === "+") return a + b;
    if (o === "−") return a - b;
    if (o === "×") return a * b;
    if (o === "÷") return b !== 0 ? a / b : 0;
    return b;
  };

  const fmt = (n) => {
    if (isNaN(n) || !isFinite(n)) return "Error";
    const s = parseFloat(n.toFixed(8)).toString();
    return s.length > 12 ? parseFloat(n.toPrecision(8)).toString() : s;
  };

  const pressEqual = () => {
    if (op === null || prev === null) return;
    const result = calc(prev, parseFloat(display), op);
    setDisplay(fmt(result));
    setPrev(null);
    setOp(null);
    setWaitNext(true);
  };

  const pressClear = () => {
    setDisplay("0");
    setPrev(null);
    setOp(null);
    setWaitNext(false);
  };

  const pressPlusMinus = () => {
    setDisplay(fmt(parseFloat(display) * -1));
  };

  const pressPct = () => {
    setDisplay(fmt(parseFloat(display) / 100));
  };

  const pressBackspace = () => {
    if (waitNext) return;
    const next = display.length > 1 ? display.slice(0, -1) : "0";
    setDisplay(next);
  };

  const rows = [
    [
      { label: "AC", action: pressClear, cls: "bg-gray-200 text-gray-800 hover:bg-gray-300" },
      { label: "+/−", action: pressPlusMinus, cls: "bg-gray-200 text-gray-800 hover:bg-gray-300" },
      { label: "%", action: pressPct, cls: "bg-gray-200 text-gray-800 hover:bg-gray-300" },
      { label: "÷", action: () => pressOp("÷"), cls: op === "÷" && waitNext ? "bg-white text-orange-500 hover:bg-orange-50" : "bg-orange-400 text-white hover:bg-orange-500" },
    ],
    [
      { label: "7", action: () => pressDigit("7"), cls: "bg-gray-700 text-white hover:bg-gray-600" },
      { label: "8", action: () => pressDigit("8"), cls: "bg-gray-700 text-white hover:bg-gray-600" },
      { label: "9", action: () => pressDigit("9"), cls: "bg-gray-700 text-white hover:bg-gray-600" },
      { label: "×", action: () => pressOp("×"), cls: op === "×" && waitNext ? "bg-white text-orange-500 hover:bg-orange-50" : "bg-orange-400 text-white hover:bg-orange-500" },
    ],
    [
      { label: "4", action: () => pressDigit("4"), cls: "bg-gray-700 text-white hover:bg-gray-600" },
      { label: "5", action: () => pressDigit("5"), cls: "bg-gray-700 text-white hover:bg-gray-600" },
      { label: "6", action: () => pressDigit("6"), cls: "bg-gray-700 text-white hover:bg-gray-600" },
      { label: "−", action: () => pressOp("−"), cls: op === "−" && waitNext ? "bg-white text-orange-500 hover:bg-orange-50" : "bg-orange-400 text-white hover:bg-orange-500" },
    ],
    [
      { label: "1", action: () => pressDigit("1"), cls: "bg-gray-700 text-white hover:bg-gray-600" },
      { label: "2", action: () => pressDigit("2"), cls: "bg-gray-700 text-white hover:bg-gray-600" },
      { label: "3", action: () => pressDigit("3"), cls: "bg-gray-700 text-white hover:bg-gray-600" },
      { label: "+", action: () => pressOp("+"), cls: op === "+" && waitNext ? "bg-white text-orange-500 hover:bg-orange-50" : "bg-orange-400 text-white hover:bg-orange-500" },
    ],
    [
      { label: "⌫", action: pressBackspace, cls: "bg-gray-700 text-white hover:bg-gray-600" },
      { label: "0", action: () => pressDigit("0"), cls: "bg-gray-700 text-white hover:bg-gray-600" },
      { label: ".", action: pressDot, cls: "bg-gray-700 text-white hover:bg-gray-600" },
      { label: "=", action: pressEqual, cls: "bg-orange-400 text-white hover:bg-orange-500" },
    ],
  ];

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white shadow-lg flex items-center justify-center transition-all active:scale-95"
        title="Calculator"
      >
        {open ? (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <rect x="4" y="2" width="16" height="20" rx="2" strokeLinecap="round" strokeLinejoin="round" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 6h8M8 10h2M12 10h2M16 10h0M8 14h2M12 14h2M16 14h0M8 18h2M12 18h2M16 18h0" />
          </svg>
        )}
      </button>

      {/* Calculator panel */}
      {open && (
        <div className="fixed bottom-24 right-6 z-50 w-64 bg-gray-800 rounded-2xl shadow-2xl overflow-hidden">
          {/* Display */}
          <div className="px-4 pt-4 pb-2 text-right">
            <p className="text-gray-400 text-xs h-4 truncate">
              {prev !== null ? `${prev} ${op}` : ""}
            </p>
            <p className="text-white text-3xl font-light truncate mt-0.5">{display}</p>
          </div>

          {/* Buttons */}
          <div className="grid grid-cols-4 gap-1.5 p-3">
            {rows.flat().map((btn, i) => (
              <button key={i} onClick={btn.action} className={`${BTN} ${btn.cls}`}>
                {btn.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
