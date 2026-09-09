// A payment path with one planted fault: the retry re-enters the PAYMENT
// call instead of the confirmation call, so a slow order is charged twice
// and the ledger total is the only thing anybody sees.
export type Order = { id: string; amount: number; slow: boolean };

const ledger: number[] = [];

export function charge(order: Order): number {
  ledger.push(order.amount);
  return ledger.length;
}

export function confirm(order: Order): boolean {
  return !order.slow;
}

export function total(): number {
  return ledger.reduce((sum, n) => sum + n, 0);
}

export function submit(order: Order): number {
  charge(order);
  if (!confirm(order)) {
    charge(order);
  }
  return total();
}
