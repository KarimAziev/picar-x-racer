import { EditorSelection } from "@codemirror/state";
import { EditorView, Command } from "@codemirror/view";

/**
 *  Implementation of Emacs command join-line for codemirror.
 *
 * Join the line to previous and fix up whitespace at join.
 *
 * If there is a fill prefix, delete it from the beginning of the line.
 */

export const joinLine: Command = (view: EditorView) => {
  const { state } = view;
  const ranges = state.selection.ranges;
  const changes: { from: number; to: number; insert: string }[] = [];
  const newRanges = [];

  for (const range of ranges) {
    const pos = range.head;
    const line = state.doc.lineAt(pos);
    const offsetInLine = pos - line.from;
    const firstNonWS =
      line.text.search(/\S/) === -1 ? line.length : line.text.search(/\S/);

    const joinWithPrevious = offsetInLine <= firstNonWS;

    if (joinWithPrevious) {
      if (line.number === 1) {
        newRanges.push(range);
        continue;
      }
      const prevLine = state.doc.line(line.number - 1);

      const wsMatch = line.text.match(/^\s*/);
      const wsLength = wsMatch ? wsMatch[0].length : 0;
      const from = prevLine.to;
      const to = line.from + wsLength;

      const left = prevLine.text.replace(/\s+$/, "");

      const right = line.text.slice(wsLength);

      const insert = left && right && !left.endsWith(" ") ? " " : "";

      changes.push({ from, to, insert });

      const newPos = prevLine.from + left.length;
      newRanges.push(EditorSelection.cursor(newPos));
    } else {
      if (line.number === state.doc.lines) {
        newRanges.push(range);
        continue;
      }
      const nextLine = state.doc.line(line.number + 1);
      const wsMatch = nextLine.text.match(/^\s*/);
      const wsLength = wsMatch ? wsMatch[0].length : 0;
      const from = line.to;
      const to = nextLine.from + wsLength;

      const left = line.text.replace(/\s+$/, "");
      const right = nextLine.text.slice(wsLength);

      const insert = left && right && !left.endsWith(" ") ? " " : "";

      changes.push({ from, to, insert });

      const newPos = line.from + left.length;
      newRanges.push(EditorSelection.cursor(newPos));
    }
  }

  if (changes.length === 0) return false;

  const tr = state.update({
    changes,
    selection: EditorSelection.create(newRanges),
    scrollIntoView: true,
  });
  view.dispatch(tr);
  return true;
};

export const smartLineStart: Command = (view: EditorView) => {
  const { state } = view;
  const ranges = state.selection.ranges;

  const newRanges = [];

  for (const range of ranges) {
    const pos = range.head;
    const line = state.doc.lineAt(pos);
    const match = line.text.match(/^\s*/);
    const indent = line.from + (match ? match[0].length : 0);

    if (pos === indent) {
      newRanges.push(EditorSelection.cursor(line.from));
    } else {
      newRanges.push(EditorSelection.cursor(indent));
    }
  }

  const tr = state.update({
    selection: EditorSelection.create(newRanges),
    scrollIntoView: true,
  });
  view.dispatch(tr);
  return true;
};
