# Current State

## Active Work

Completing class and method semantics, particularly callable references, bound method resolution, and function return values.

The HIR-to-LIR lowering code is also being adapted to the updated assignment and call target representation.

### Current IR Changes

- `AssignIR` no longer uses a separate `name` and `field` representation. Its `target` is either `IdentifierIR` or `FieldAccessIR`.
- `CallIR` is moving from `name` to `target`, with the same target contract: `IdentifierIR` or `FieldAccessIR`.
- LIR generation must distinguish identifier calls from field/method calls and preserve receiver evaluation.
- These changes are still being integrated; do not consider the lowering implementation fully verified yet.

## Known Issues

- **Callable return values lose their callable semantics.**

  When a function returns a bound method reference, Auto Type Def currently preserves the original function reference instead of resolving the callable type of its return value.

  Consequently, calling the returned reference incorrectly uses the original function's argument requirements rather than the bound method's signature.

- Function references and callable values returned from functions need broader testing. Their type information, argument handling, and receiver binding are not yet fully verified.

## Working Features

- Class declarations and instance field access through `self`.
- Constructor initialization and argument handling.
- Bound method references and aliases.
- Multiple references to the same method with different receivers.
- Instance mutations through original and aliased method references.
- Nested object references and mutations.
- Method access and bound method references on method-call results.
- Cross-instance method calls and object interactions.
- Method forwarding and reference preservation.
- Object composition and mutations across multiple instances.
- Receiver expressions can be materialized as intermediate values in HIR Passer and passed as implicit `self`.

A comprehensive local regression program covering method references, aliases, nested receivers, mutations, forwarding, and cross-instance interactions compiles and executes successfully.

## Next Steps

- Fix callable return-value resolution, especially functions returning bound method references.
- Preserve bound receiver identity when a method reference is returned from a