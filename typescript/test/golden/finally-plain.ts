export function cleanupOnly(): void {
  try {
    risky();
  } finally {
    cleanup();
  }
}

for (const item of items) {
  try {
    risky();
  } finally {
    break;
  }
}
