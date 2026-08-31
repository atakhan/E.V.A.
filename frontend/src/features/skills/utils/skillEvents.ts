export interface EventCorrelation {
  conversationId?: string;
  entityId?: string;
  skillRunId?: string;
  actionRunId?: string;
  agentId?: string;
  requestId?: string;
  parentRunId?: string;
  userId?: string;
}

/** Domain Event envelope per EVENT_SPEC v0.1 */
export interface EvaEvent {
  id: string;
  type: string;
  version: string;
  source: string;
  timestamp: string;
  correlation: EventCorrelation;
  payload: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  causationId?: string;
}

export const COMMON_DOMAIN_EVENTS = [
  "channel.message.received",
  "channel.message.sent",
  "supplier.reply.received",
  "request.created",
  "request.updated",
  "invoice.received",
  "human.request.approved",
  "human.request.corrected",
  "shipment.updated",
  "timer.elapsed",
] as const;

export function actionCompletedEvent(actionId: string): string {
  return `action.${actionId}.completed`;
}

export function suggestedSkillEvents(actionIds: string[]): string[] {
  const actionEvents = actionIds.map((actionId) => actionCompletedEvent(actionId));
  return [...COMMON_DOMAIN_EVENTS, ...actionEvents];
}
