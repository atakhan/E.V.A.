export const COMMON_TEMPLATE_TOKENS = [
  "{{vars.last_message}}",
  "{{vars.conversation_id}}",
  "{{input.text}}",
  "{{input.request_id}}",
  "{{steps.prev.result}}",
] as const;

export function insertAtCursor(element: HTMLInputElement | HTMLTextAreaElement, token: string) {
  const start = element.selectionStart ?? element.value.length;
  const end = element.selectionEnd ?? element.value.length;
  const next = `${element.value.slice(0, start)}${token}${element.value.slice(end)}`;
  element.value = next;
  const caret = start + token.length;
  element.setSelectionRange(caret, caret);
  element.dispatchEvent(new Event("input", { bubbles: true }));
  element.focus();
}
