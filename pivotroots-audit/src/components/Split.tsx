/**
 * Headline words wrapped for the rise-in reveal: each word sits in an
 * overflow-hidden box and slides up when its heading (marked data-split) gets
 * the .in class from MotionRoot. Rendered on the server, so the text is in the
 * HTML as-is; --i staggers the words.
 */
import { Fragment, type CSSProperties } from "react";

export function Word({ i, children }: { i: number; children: React.ReactNode }) {
  return <span className="w"><span className="wi" style={{ "--i": i } as CSSProperties}>{children}</span></span>;
}

export function Words({ text, start = 0 }: { text: string; start?: number }) {
  return (
    <>
      {text.split(" ").map((w, i) => (
        <Fragment key={i}>{i > 0 && " "}<Word i={start + i}>{w}</Word></Fragment>
      ))}
    </>
  );
}

/** Lines separated by <br />, words numbered across all of them. */
export function Lines({ lines }: { lines: string[] }) {
  const starts = lines.map((_, i) => lines.slice(0, i).reduce((sum, l) => sum + l.split(" ").length, 0));
  return (
    <>
      {lines.map((l, i) => <Fragment key={i}>{i > 0 && <br />}<Words text={l} start={starts[i]} /></Fragment>)}
    </>
  );
}
