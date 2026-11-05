# Nidavellir Programming Language

> **⚠️ Experimental Project — Not Ready for Production Use**
>
> Nidavellir is currently in an early experimental development stage and is **not yet ready for general use or production workloads**. The language, compiler architecture, syntax, and internal APIs are actively evolving and may change or break without notice.
>
> This repository is currently intended for experimentation, compiler development, and contributors interested in following the project's progress. Cloning or testing it is welcome, but please do not rely on it for real-world projects yet.

## Identity & Core Philosophy

- **Language vs. Driver**: **Nidavellir** is the programming language (source files use the `.nida` extension). **`nidac`** is the compiler driver.
- **Bootstrap Implementation**: The compiler frontend is currently implemented in Python as a bootstrapping stage. The long-term architectural goal is a self-hosting compiler.
- **Native Execution**: `nidac` compiles source code into native executables by generating C target code and invoking the native compiler toolchain (GCC/Clang). It does not use a virtual machine (VM), bytecode interpreter, or JIT engine as its primary execution model.
- **Static Typing without Annotation Overhead**: Variables in Nidavellir are statically typed, but explicit type annotations (such as `u8 a = 2`) are normally unnecessary. Static representations are determined at compile time using static analysis, dataflow propagation, and range reasoning.
- **Fixed Compile-Time Types**: Type inference operates statically before code generation. Inferred types do not change at runtime.
- **Opt-in Dynamic Semantics**: The language is designed to support an explicit `@dynamic` directive for cases where dynamic behavior is requested.
- **Top-Level Code**: Source files do not require a mandatory C-style `main()` function. Top-level statements are placed directly into the program entry point by the compilation pipeline.

---

## AutoTypeDef & Range Analysis

The `AutoTypeDef` system performs static range, interval, and constraint reasoning across expressions, loops, and control flow paths.

The static analysis engine evaluates:
- Integer constants and arithmetic expressions
- Binary operations and comparison predicates
- Symbol usage and dataflow constraints
- Function parameters and return values
- Loop bounds and loop-carried variable updates
- Control-flow branch paths
- Division and modulo safety, including compile-time division-by-zero detection

### Example: Compile-Time Range Analysis

```python
a = 2
c = 0
while c < 10:
    print(a)
    c += 1
    a *= c
```

The initial value `a = 2` does not restrict `a` to a minimal type if subsequent loop operations increase its value range. The `AutoTypeDef` engine evaluates potential value bounds across loop iterations at compile time and assigns a suitable fixed integer representation (e.g., `u8`, `u16`, `u32`, `u64`).

*Note: Current range analysis evaluates bounds during compilation passes. A generalized fixed-point abstract interpretation dataflow solver is planned as future work.*

---

## Memory Model

Nidavellir does not use a garbage collector (GC) or a managed runtime. The language is designed around explicit memory management and compiler-controlled allocation.

The following memory-management features are part of the language design and are planned for implementation:

- **Allocation Strategy Directives**: `@use_stack`, `@alwaysStack`, `@alwaysHeap`, and `@useMalloc` for explicitly selecting memory allocation strategies.
- **Low-Level Safety**: Ownership and lifetime verification are planned as part of the language's low-level memory architecture.

## Compiler Pipeline & Intermediate Representations

The conceptual compilation pipeline is:

```
Source Code (.nida)
        │
        ▼
   [Lexer Engine]
        │  (Tokens)
        ▼
   [Parser Engine]
        │  (Abstract Syntax Tree - AST)
        ▼
[Import-Tree Analysis]
        │  (Direct C Header/Library Parsing)
        ▼
[Semantic / Symbol Analyzer]
        │  (Symbol Table & Scope Resolution)
        ▼
[AutoTypeDef Engine]
        │  (Static Range & Interval Reasoning)
        ▼
  [HIR Generator]
        │  (High-Level Intermediate Representation)
        ▼
  [HIR Passes / Lowering]
        │
        ▼
  [LIR Lowerer]
        │  (Low-Level IR & Basic-Block CFG)
        ▼
 [C Backend Generator]
        │  (C Target Source Code)
        ▼
 [GCC / Clang Toolchain]
        │
        ▼
 Native Binary Executable
```

### Intermediate Representations (HIR and LIR)

HIR and LIR are Nidavellir's actual internal intermediate representations. C is not an intermediate representation; it is the backend target output emitted for consumption by GCC or Clang.

- **HIR (High-Level Intermediate Representation)**: Preserves semantic language-level structures for high-level compiler passes and analysis.
- **LIR (Low-Level Intermediate Representation)**: A lower-level representation structured around basic blocks and explicit value instructions.
  - LIR primitives include `ConstLIR`, `LoadLIR`, `StoreLIR`, `DeclareLIR`, `CallLIR`, `ReturnLIR`, `AddLIR`, `SubLIR`, `MulLIR`, `DivLIR`, `ModLIR`, `GtLIR`, `LtLIR`, `ArgLIR`, `BlockLIR`, `JumpLIR`, `BranchLIR`, `ReturnLIR`, and `FunctionLIR`.
  - **Declaration vs. Assignment**: Variable definition (`DeclareLIR`) and assignment to an existing variable (`StoreLIR`) are semantically distinct LIR operations.

### Control Flow Graph (CFG) & Basic Blocks

Control-flow structures (`if`, `elif`, `else`, `while`) are lowered into basic blocks (`BlockLIR`) terminated strictly by control-flow instructions (`JumpLIR`, `BranchLIR`, `ReturnLIR`).

- No normal instructions are emitted after a block terminator.
- Block IDs and Value IDs exist in separate namespaces.
- Conceptual basic-block lowering for a `while` loop:
  ```
  Bcond:
      evaluate condition
      BranchLIR condition, Bbody, Bmerge

  Bbody:
      loop body statements
      JumpLIR Bcond

  Bmerge:
      continuation statements
  ```

---

## C Backend & Direct C Header/Library Import

### C Backend Target

The C backend is an intentional target emission format used to produce native binaries via GCC or Clang while maintaining ABI compatibility with existing C libraries. 

Nidavellir semantics are fully analyzed and lowered into HIR and LIR before C emission occurs. Therefore, C code emission is an intermediate code generation step rather than a syntax-to-syntax transpilation pass.

### Direct C ABI Integration

Nidavellir supports importing C headers and native libraries directly through its import syntax:

```python
from math import cos

res = cos(3.14159)
```

- Imported C symbols are parsed directly into the compiler's symbol table and participate in type analysis.
- Symbols are namespaced where necessary to avoid collisions.
- C header integration operates at compile time and does not use IPC, dynamic runtime bridges, or Python `ctypes`/`cffi` marshaling.

---

## Native Runtime Support

Nidavellir includes a C runtime support layer (`Nida_core.h`, `print.h`).

This runtime provides helper infrastructure for generated C code (such as print functions and core runtime primitives). It is not a virtual machine and does not execute or interpret bytecode.

---

## Planned Compiler Directives

The following directives are part of the language design but are not implemented yet:

- `@nidac(pedantic)` — strict compiler diagnostics.
- `@use_stack`, `@alwaysStack`, `@alwaysHeap`, `@useMalloc` — explicit memory strategy selection.

---

## Current Project Status vs. Roadmap

### Implemented & Verified
- [x] Pure Python Lexer & Tokenizer
- [x] Recursive Descent AST Parser
- [x] Symbol Table & Scope Analysis
- [x] Import-Tree Analysis & Direct C Header/Library Parsing
- [x] Semantic Analyzer & AutoTypeDef Range Engine
- [x] High-Level IR (HIR) Generation & Lowering Passes
- [x] Low-Level IR (LIR) & Basic-Block CFG Lowering (`if`, `while`, `BranchLIR`, `JumpLIR`, `DeclareLIR`, `StoreLIR`)
- [x] C Backend Code Generation & GCC/Clang Toolchain Integration
- [x] Native C Runtime Infrastructure (`Nida_core.h`, `print.h`)

### Planned / Future Roadmap
- [ ] LLVM IR Backend Target
- [ ] Fixed-Point Abstract Interpretation Dataflow Solver
- [ ] Ownership & Lifetime Analysis
- [ ] Polymorphic Function Monomorphization

---

## Building and Running Tests

```bash
# Run unit test suite
python3 -m unittest discover -s test

# Run compiler driver test script
python3 t_test_.py
```
