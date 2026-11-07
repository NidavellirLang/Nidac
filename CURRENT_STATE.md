# Current State

## Active Work
Refactoring the Symbol system and type definitions.

## Known Issues
- Some AST visitors in the analyzer still use outdated Symbol constructors.
- SymbolTable compatibility has not yet been verified.
- Type inference for class methods that accept arguments is currently incorrect.
- Nested class-method calls fail to resolve the receiver's `self` correctly. For example, `self.nm.print_name()` raises `Function 'self' is not defined` in `resolve_call_lookup`.

## Next Steps
- Refactor remaining AST visitors.
- Verify SymbolTable compatibility.
- Fix type inference for class methods with arguments.
- Fix `self` resolution in nested/chained class-method calls.
- Run semantic analyzer regression tests.