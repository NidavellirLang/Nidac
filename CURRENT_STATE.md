# Current State

## Active Work
Refactoring the Symbol system and type definitions.

## Known Issues
- Class constructor argument count errors can cause Python `IndexError` instead of a proper Nidavellir error.
- Class fields declared at class scope can incorrectly appear accessible inside methods without `self` (e.g. `name = "Nidavellir"`).
- Instance field access through `self` is not resolved correctly inside methods (e.g. `print(self.name)` fails).
- Some AST visitors in the analyzer still use outdated Symbol constructors.
- SymbolTable compatibility has not yet been verified.

## Next Steps
- Fix constructor argument count validation.
- Fix class field name resolution inside methods.
- Refactor remaining AST visitors to use updated Symbol constructors.
- Verify SymbolTable compatibility.
- Expand semantic analyzer regression tests.
- Complete class and method semantics before moving on to compiler optimizations.