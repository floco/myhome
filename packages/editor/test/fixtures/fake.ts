/**
 * Partial test double typed as whatever the call site expects.
 *
 * Component tests hand stores and models to components with only the fields
 * the test exercises. `fake({...})` takes its type from context (a prop, a
 * parameter, a typed variable), so the double type-checks without spelling
 * out every unused member, and a typo'd field name still shows up when the
 * component reads it at runtime.
 */
export function fake<T>(partial: object): T {
  return partial as T;
}
