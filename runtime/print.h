#ifndef PRINT_H
#define PRINT_H

#include <stdio.h>
#include <stdbool.h>
#include <stdint.h>
#include <locale.h>
#include "Nida_core.h"

#if defined(_WIN32) || defined(_WIN64)
#include <windows.h>
static inline void _Nida_setup_platform_utf8(void)
{
  SetConsoleOutputCP(65001);
  SetConsoleCP(65001);
  HANDLE hOut = GetStdHandle(STD_OUTPUT_HANDLE);
  if (hOut != INVALID_HANDLE_VALUE)
  {
    DWORD dwMode = 0;
    if (GetConsoleMode(hOut, &dwMode))
    {
      SetConsoleMode(hOut, dwMode | 0x0004);
    }
  }
}
#else
static inline void _Nida_setup_platform_utf8(void)
{
  setlocale(LC_ALL, "");
}
#endif

static inline void Nida_init_terminal(void)
{
  static bool initialized = false;
  if (!initialized)
  {
    _Nida_setup_platform_utf8();
    initialized = true;
  }
}

typedef enum
{
  NIDA_TYPE_INT,
  NIDA_TYPE_DOUBLE,
  NIDA_TYPE_STR,
  NIDA_TYPE_NIDA_STR,
  NIDA_TYPE_BOOL,
  NIDA_TYPE_CHAR,
  NIDA_TYPE_PTR,
  NIDA_TYPE_NONE
} NidaType;

typedef struct
{
  NidaType type;
  union
  {
    long long num;
    double dbl;
    const char *str;
    Nida_Str nstr;
    bool boolean;
    char ch;
    const void *ptr;
  } value;
} NidaVal;

static inline NidaVal _Nida_make_int(long long v) { return (NidaVal){.type = NIDA_TYPE_INT, .value.num = v}; }
static inline NidaVal _Nida_make_dbl(double v) { return (NidaVal){.type = NIDA_TYPE_DOUBLE, .value.dbl = v}; }
static inline NidaVal _Nida_make_str(const char *v) { return (NidaVal){.type = NIDA_TYPE_STR, .value.str = v}; }
static inline NidaVal _Nida_make_bool(bool v) { return (NidaVal){.type = NIDA_TYPE_BOOL, .value.boolean = v}; }
static inline NidaVal _Nida_make_char(char v) { return (NidaVal){.type = NIDA_TYPE_CHAR, .value.ch = v}; }

static inline NidaVal _Nida_make_ptr_or_none(const void *v)
{
  if (v == NIDA_NONE_ADDR)
  {
    return (NidaVal){.type = NIDA_TYPE_NONE};
  }
  return (NidaVal){.type = NIDA_TYPE_PTR, .value.ptr = v};
}

static inline NidaVal _Nida_make_Nida_str(Nida_Str v) { return (NidaVal){.type = NIDA_TYPE_NIDA_STR, .value.nstr = v}; }

#define NIDA_VAL(x) _Generic((x),       \
    bool: _Nida_make_bool,              \
    char: _Nida_make_char,              \
    signed char: _Nida_make_int,        \
    unsigned char: _Nida_make_int,      \
    short: _Nida_make_int,              \
    unsigned short: _Nida_make_int,     \
    int: _Nida_make_int,                \
    unsigned int: _Nida_make_int,       \
    long: _Nida_make_int,               \
    unsigned long: _Nida_make_int,      \
    long long: _Nida_make_int,          \
    unsigned long long: _Nida_make_int, \
    float: _Nida_make_dbl,              \
    double: _Nida_make_dbl,             \
    char *: _Nida_make_str,             \
    const char *: _Nida_make_str,       \
    void *: _Nida_make_ptr_or_none,     \
    Nida_Str: _Nida_make_Nida_str,      \
    const void *: _Nida_make_ptr_or_none)(x)

static inline void _Nida_print_chunk(size_t count, const NidaVal args[], bool is_last)
{
  Nida_init_terminal();
  for (size_t i = 0; i < count; i++)
  {
    switch (args[i].type)
    {
    case NIDA_TYPE_INT:
      printf("%lld", args[i].value.num);
      break;
    case NIDA_TYPE_DOUBLE:
      printf("%g", args[i].value.dbl);
      break;
    case NIDA_TYPE_STR:
      printf("%s", args[i].value.str ? args[i].value.str : "None");
      break;
    case NIDA_TYPE_NIDA_STR:
      Nida_str_print(args[i].value.nstr);
      break;
    case NIDA_TYPE_BOOL:
      printf("%s", args[i].value.boolean ? "true" : "false");
      break;
    case NIDA_TYPE_CHAR:
      printf("%c", args[i].value.ch);
      break;
    case NIDA_TYPE_PTR:
      printf("%p", args[i].value.ptr);
      break;
    case NIDA_TYPE_NONE:
      printf("None");
      break;
    }

    if (i + 1 < count)
    {
      printf(" ");
    }
  }

  if (is_last)
  {
    printf("\n");
  }
  else
  {
    printf(" ");
  }
}

#define _Nida_print_a1(a, is_last) \
  _Nida_print_chunk(1, (NidaVal[]){NIDA_VAL(a)}, is_last)

#define _Nida_print_a2(a, b, is_last) \
  _Nida_print_chunk(2, (NidaVal[]){NIDA_VAL(a), NIDA_VAL(b)}, is_last)

#define _Nida_print_a3(a, b, c, is_last) \
  _Nida_print_chunk(3, (NidaVal[]){NIDA_VAL(a), NIDA_VAL(b), NIDA_VAL(c)}, is_last)

#define _Nida_print_a4(a, b, c, d, is_last) \
  _Nida_print_chunk(4, (NidaVal[]){NIDA_VAL(a), NIDA_VAL(b), NIDA_VAL(c), NIDA_VAL(d)}, is_last)

#define Nida_print_a1(a) _Nida_print_a1(a, true)
#define Nida_print_a2(a, b) _Nida_print_a2(a, b, true)
#define Nida_print_a3(a, b, c) _Nida_print_a3(a, b, c, true)
#define Nida_print_a4(a, b, c, d) _Nida_print_a4(a, b, c, d, true)

#endif