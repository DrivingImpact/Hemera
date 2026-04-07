export function fmtTonnes(value: number): string {
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`;
  return value.toFixed(1);
}

export function fmtGBP(value: number): string {
  return new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP", maximumFractionDigits: 0 }).format(value);
}

export function fmtPct(value: number): string {
  return `${value.toFixed(1)}%`;
}

export function fmtNumber(value: number): string {
  return new Intl.NumberFormat("en-GB").format(Math.round(value));
}
