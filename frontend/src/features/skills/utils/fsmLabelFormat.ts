export function truncateLabelText(value: string, maxLength: number): string {
  if (value.length <= maxLength) return value;
  return `${value.slice(0, maxLength - 1)}…`;
}

export function formatUmlActionsSegment(actions: string[]): string | null {
  if (actions.length === 0) return null;
  if (actions.length <= 3) return actions.join(", ");
  return `${actions.slice(0, 2).join(", ")} +${actions.length - 2}`;
}

export function formatUmlEntryLine(actions: string[]): string | null {
  const segment = formatUmlActionsSegment(actions);
  if (!segment) return null;
  return `entry / ${segment}`;
}

export interface UmlTransitionLabel {
  triggerLine: string;
  actionLine: string | null;
  title: string;
  width: number;
  height: number;
  labelLines: { triggerY: number; actionY?: number };
}

const TRIGGER_CHAR_WIDTH = 6.7;
const ACTION_CHAR_WIDTH = 6.1;
const LABEL_PADDING = 14;
const TRIGGER_LINE_HEIGHT = 14;
const ACTION_LINE_HEIGHT = 11;
const MAX_LABEL_WIDTH = 280;
const MAX_LABEL_WIDTH_SELECTED = 360;

function truncateToWidth(text: string, charWidth: number, maxWidth: number): string {
  const maxChars = Math.max(4, Math.floor((maxWidth - LABEL_PADDING) / charWidth));
  return truncateLabelText(text, maxChars);
}

function lineWidth(text: string, charWidth: number): number {
  return Math.ceil(text.length * charWidth + LABEL_PADDING);
}

export function formatUmlTransitionLabel(
  event: string,
  guard: string,
  actions: string[],
  selected: boolean,
  labelCenterY: number,
): UmlTransitionLabel {
  const eventPart = (event.trim() || "event");
  const guardPart = guard.trim();
  const guardInTrigger = guardPart ? ` [${guardPart}]` : "";
  const maxWidth = selected ? MAX_LABEL_WIDTH_SELECTED : MAX_LABEL_WIDTH;
  const triggerLine = truncateToWidth(`${eventPart}${guardInTrigger}`, TRIGGER_CHAR_WIDTH, maxWidth);

  const actionsSegment = formatUmlActionsSegment(actions);
  const actionLineRaw = actionsSegment ? `/ ${actionsSegment}` : null;
  const actionLine = actionLineRaw
    ? truncateToWidth(actionLineRaw, ACTION_CHAR_WIDTH, maxWidth)
    : null;

  const title = actionLineRaw
    ? `${eventPart}${guardInTrigger} ${actionLineRaw}`
    : `${eventPart}${guardInTrigger}`;

  const widths = [
    lineWidth(triggerLine, TRIGGER_CHAR_WIDTH),
    actionLine ? lineWidth(actionLine, ACTION_CHAR_WIDTH) : 0,
  ];
  const width = Math.max(48, ...widths.filter((item) => item > 0));

  let height = TRIGGER_LINE_HEIGHT + 4;
  if (actionLine) height += ACTION_LINE_HEIGHT;

  const top = labelCenterY - height / 2;
  const triggerY = actionLine ? top + 11 : labelCenterY + 3.5;
  const actionY = actionLine ? top + 22 : undefined;

  return {
    triggerLine,
    actionLine,
    title,
    width,
    height,
    labelLines: { triggerY, actionY },
  };
}
