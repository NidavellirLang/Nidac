# Current State

## Active Work

New HIR passer architecture (HIR → MIR → LIR) with bound method lowering, class
lowering, and callable reference support.

## Current IR

- `AssignIR.target` is either `IdentifierIR` or `FieldAccessIR`.
- `CallIR.target` follows the same contract. `CallIR.indirect` marks
  field-based function-pointer calls.
- `BoundMethodIR` / `BoundCallIR` represent callable values and their calls.
- `FunctionRefIR` carries a function pointer value.
- `ClassLowering` lowers classes, methods, `self` binding, and call targets.
- `BoundMethods` lowers callable references into a single generic
  `{ self, fn }` struct plus one initializer function.
- `CollectMain` gathers top-level statements into `main`.
- Default pipeline: `ClassLowering → BoundMethods → CollectMain`.
- `IRTransform.targets` allows a pass to visit only selected IR types.
- `PassManager` injects the per-run `ctx` into each transform.

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
- Receiver expressions materialized as intermediate values in HIR Passer and
  passed as implicit `self`.
- Bound method references returned from functions, both assigned to a local
  first and returned directly; the returned reference keeps its receiver and
  signature.
- Recursive function type inference (parameter seeding from literal call sites,
  provisional return types, cycle guards in Auto Type Def).
- Correct `if` block ordering in LIR (then → false → merge).

## Known Limitations

- Index access (`s[i]`) is not implemented beyond the parser: no semantic
  `eval_IndexAccessAST`, no `IndexAccessIR`, no LIR/C lowering.
- `len` / `ord` are not registered intrinsics yet, although the runtime
  provides `Nida_str_len` / `Nida_str_ord` / `Nida_str_ord0`.
- Callable values in arbitrary expression positions (e.g. passed as arguments)
  are not supported; lowering covers assignments and returns.

## Runtime

- `Nida_Str` uses a PEP 393-style flexible representation:
  `{ void *data; size_t length; uint8_t kind; }` with 1/2/4-byte code units.
- Implementation is header-only in `runtime/Nida_str.h` (`static inline`), so no
  extra C translation unit is linked in. UTF-8 encode/decode, validation, concat,
  equality, indexing, `len`, `ord`, `ord0`, and emptiness are available.

## Next Steps

- Implement index access end to end.
- Wire `len` / `ord` intrinsics to the new string representation.
- Extend callable-value lowering to argument positions.
- Add scope/lifetime analysis to decide when bound-method structs and class
  instances can stay on the stack or be captured.
