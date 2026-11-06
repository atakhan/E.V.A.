/** Shared flight pose for desk icon / Eva / runtime handoffs. */
export type Flight = {
  dx: number;
  dy: number;
  scale: number;
};

export function flightIdentity(): Flight {
  return { dx: 0, dy: 0, scale: 1 };
}

export function flightTo(
  from: { x: number; y: number },
  to: { x: number; y: number },
  scale: number,
): Flight {
  return {
    dx: to.x - from.x,
    dy: to.y - from.y,
    scale,
  };
}
