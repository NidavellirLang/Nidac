#ifndef NIDA_STR_H
#define NIDA_STR_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef struct
{
  void *data;
  size_t length;
  uint8_t kind;
} Nida_Str;

Nida_Str Nida_str_new(const char *cstr);
Nida_Str Nida_str_from_literal(const char *cstr);
Nida_Str Nida_str_from_utf8(const char *bytes, size_t byte_len);
void Nida_str_free(Nida_Str *s);

Nida_Str Nida_str_concat(Nida_Str a, Nida_Str b);
bool Nida_str_eq(Nida_Str a, Nida_Str b);
bool Nida_str_not(Nida_Str s);
Nida_Str Nida_str_index(Nida_Str s, size_t index);

size_t Nida_str_len(Nida_Str s);
int64_t Nida_str_ord(Nida_Str s, size_t index, bool *ok);
int64_t Nida_str_ord0(Nida_Str s);

bool Nida_str_is_valid_utf8(const char *bytes, size_t byte_len);
char *Nida_str_to_utf8(Nida_Str s, size_t *out_len);

void Nida_str_print(Nida_Str s);

#endif // NIDA_STR_H
