/**
 * FlowForge TypeScript Client - Events Resource
 */

import { QueryBuilder, type RequestFn } from "../builder";
import type {
  Event,
  EventFilters,
  SendEventResponse,
  SendEventInput,
  Result,
} from "../types";

export class EventsResource {
  constructor(private request: RequestFn) {}

  /**
   * Send an event to trigger matching workflows.
   *
   * @example
   * ```ts
   * const { data, error } = await ff.events.send('order/created', {
   *   order_id: '123',
   *   customer: 'Alice'
   * });
   * if (error) console.error(error.message);
   * else console.log('Triggered runs:', data.runs);
   * ```
   */
  async send(
    name: string,
    data: Record<string, unknown>,
    options?: SendEventInput
  ): Promise<Result<SendEventResponse>> {
    return this.request<SendEventResponse>("POST", "/events", {
      name,
      data,
      id: options?.id,
      user_id: options?.user_id,
      timestamp: options?.timestamp,
    });
  }

  /**
   * Get a specific event by ID.
   *
   * @example
   * ```ts
   * const { data: event } = await ff.events.get('event-id');
   * ```
   */
  async get(eventId: string): Promise<Result<Event>> {
    return this.request<Event>("GET", `/events/${eventId}`);
  }

  /**
   * Start building a query to select events.
   *
   * @example
   * ```ts
   * const { data: events } = await ff.events
   *   .select()
   *   .eq('name', 'order/*')
   *   .limit(10)
   *   .execute();
   * ```
   */
  select(): QueryBuilder<Event, EventFilters> {
    return new QueryBuilder<Event, EventFilters>(
      this.request,
      "/events",
      "events"
    );
  }
}
