#include "Nida_str.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define NIDA_STR_MAX_CP 0x10FFFFu
#define NIDA_STR_SURROGATE_MIN 0xD800u
#define NIDA_STR_SURROGATE_MAX 0xDFFFu

static uint8_t nida_kind_for(uint32_t cp)
{
  if (cp <= 0xFFu)
    return 1;
  if (cp <= 0xFFFFu)
    return 2;
  return 4;
}

static size_t nida_unit_size(uint8_t kind)
{
  return kind == 1 ? 1 : (kind == 2 ? 2 : 4);
}

static uint32_t nida_get(const Nida_Str *s, size_t index)
{
  switch (s->kind)
  {
  case 1:
    return ((const uint8_t *)s->data)[index];
  case 2:
    return ((const uint16_t *)s->data)[index];
  default:
    return ((const uint32_t *)s->data)[index];
  }
}

static void nida_set(void *data, uint8_t kind, size_t index, uint32_t cp)
{
  switch (kind)
  {
  case 1:
    ((uint8_t *)data)[index] = (uint8_t)cp;
    break;
  case 2:
    ((uint16_t *)data)[index] = (uint16_t)cp;
    break;
  default:
    ((uint32_t *)data)[index] = cp;
    break;
  }
}

static Nida_Str nida_alloc(uint8_t kind, size_t length);

static Nida_Str nida_single(uint32_t cp)
{
  uint8_t kind = nida_kind_for(cp);
  Nida_Str s = nida_alloc(kind, 1);

  if (s.data != NULL)
    nida_set(s.data, kind, 0, cp);

  return s;
}

static Nida_Str nida_alloc(uint8_t kind, size_t length)
{
  Nida_Str s;
  size_t unit = nida_unit_size(kind);

  if (length > (SIZE_MAX / unit) - 1)
    return (Nida_Str){NULL, 0, 1};

  s.data = calloc(length + 1, unit);
  s.length = s.data ? length : 0;
  s.kind = 1;

  if (s.data)
    s.kind = kind;

  return s;
}

static bool nida_decode_one(const unsigned char *bytes, size_t len, size_t *pos, uint32_t *cp)
{
  size_t i = *pos;
  unsigned char b0 = bytes[i];
  uint32_t value;
  size_t extra;
  uint32_t minimum;

  if (b0 < 0x80u)
  {
    *cp = b0;
    *pos = i + 1;
    return true;
  }

  if ((b0 & 0xE0u) == 0xC0u)
  {
    value = b0 & 0x1Fu;
    extra = 1;
    minimum = 0x80u;
  }
  else if ((b0 & 0xF0u) == 0xE0u)
  {
    value = b0 & 0x0Fu;
    extra = 2;
    minimum = 0x800u;
  }
  else if ((b0 & 0xF8u) == 0xF0u)
  {
    value = b0 & 0x07u;
    extra = 3;
    minimum = 0x10000u;
  }
  else
  {
    return false;
  }

  if (i + extra >= len)
    return false;

  for (size_t k = 1; k <= extra; k++)
  {
    unsigned char bk = bytes[i + k];
    if ((bk & 0xC0u) != 0x80u)
      return false;
    value = (value << 6) | (bk & 0x3Fu);
  }

  if (value < minimum || value > NIDA_STR_MAX_CP)
    return false;
  if (value >= NIDA_STR_SURROGATE_MIN && value <= NIDA_STR_SURROGATE_MAX)
    return false;

  *cp = value;
  *pos = i + extra + 1;
  return true;
}

static size_t nida_encode_one(uint32_t cp, char out[4])
{
  if (cp < 0x80u)
  {
    out[0] = (char)cp;
    return 1;
  }
  if (cp < 0x800u)
  {
    out[0] = (char)(0xC0u | (cp >> 6));
    out[1] = (char)(0x80u | (cp & 0x3Fu));
    return 2;
  }
  if (cp < 0x10000u)
  {
    out[0] = (char)(0xE0u | (cp >> 12));
    out[1] = (char)(0x80u | ((cp >> 6) & 0x3Fu));
    out[2] = (char)(0x80u | (cp & 0x3Fu));
    return 3;
  }
  out[0] = (char)(0xF0u | (cp >> 18));
  out[1] = (char)(0x80u | ((cp >> 12) & 0x3Fu));
  out[2] = (char)(0x80u | ((cp >> 6) & 0x3Fu));
  out[3] = (char)(0x80u | (cp & 0x3Fu));
  return 4;
}

bool Nida_str_is_valid_utf8(const char *bytes, size_t byte_len)
{
  if (bytes == NULL)
    return byte_len == 0;

  size_t pos = 0;
  uint32_t cp;

  while (pos < byte_len)
  {
    if (!nida_decode_one((const unsigned char *)bytes, byte_len, &pos, &cp))
      return false;
  }

  return true;
}

Nida_Str Nida_str_from_utf8(const char *bytes, size_t byte_len)
{
  if (bytes == NULL)
    byte_len = 0;

  if (!Nida_str_is_valid_utf8(bytes, byte_len))
    return (Nida_Str){NULL, 0, 1};

  uint8_t kind = 1;
  size_t length = 0;
  size_t pos = 0;
  uint32_t cp;

  while (pos < byte_len)
  {
    nida_decode_one((const unsigned char *)bytes, byte_len, &pos, &cp);
    uint8_t needed = nida_kind_for(cp);
    if (needed > kind)
      kind = needed;
    length++;
  }

  Nida_Str s = nida_alloc(kind, length);
  if (s.data == NULL)
    return s;

  pos = 0;
  for (size_t i = 0; i < length; i++)
  {
    nida_decode_one((const unsigned char *)bytes, byte_len, &pos, &cp);
    nida_set(s.data, kind, i, cp);
  }

  return s;
}

Nida_Str Nida_str_new(const char *cstr)
{
  return Nida_str_from_utf8(cstr, cstr ? strlen(cstr) : 0);
}

Nida_Str Nida_str_from_literal(const char *cstr)
{
  return Nida_str_from_utf8(cstr, cstr ? strlen(cstr) : 0);
}

void Nida_str_free(Nida_Str *s)
{
  if (s == NULL || s->data == NULL)
    return;

  free(s->data);
  s->data = NULL;
  s->length = 0;
  s->kind = 1;
}

Nida_Str Nida_str_concat(Nida_Str a, Nida_Str b)
{
  if (a.data == NULL)
    return Nida_str_new(NULL);
  if (b.data == NULL)
    return Nida_str_new(NULL);

  if (a.length > SIZE_MAX - b.length)
    return (Nida_Str){NULL, 0, 1};

  uint8_t kind = a.kind > b.kind ? a.kind : b.kind;
  size_t length = a.length + b.length;

  Nida_Str s = nida_alloc(kind, length);
  if (s.data == NULL)
    return s;

  for (size_t i = 0; i < a.length; i++)
    nida_set(s.data, kind, i, nida_get(&a, i));

  for (size_t i = 0; i < b.length; i++)
    nida_set(s.data, kind, a.length + i, nida_get(&b, i));

  return s;
}

bool Nida_str_eq(Nida_Str a, Nida_Str b)
{
  if (a.length != b.length)
    return false;

  if (a.data == b.data)
    return true;

  if (a.data == NULL || b.data == NULL)
    return false;

  for (size_t i = 0; i < a.length; i++)
  {
    if (nida_get(&a, i) != nida_get(&b, i))
      return false;
  }

  return true;
}

bool Nida_str_not(Nida_Str s)
{
  return s.data == NULL || s.length == 0;
}

Nida_Str Nida_str_index(Nida_Str s, size_t index)
{
  if (s.data == NULL || index >= s.length)
    return Nida_str_new(NULL);

  return nida_single(nida_get(&s, index));
}

size_t Nida_str_len(Nida_Str s)
{
  return s.length;
}

int64_t Nida_str_ord(Nida_Str s, size_t index, bool *ok)
{
  if (s.data == NULL || index >= s.length)
  {
    if (ok != NULL)
      *ok = false;
    return -1;
  }

  if (ok != NULL)
    *ok = true;

  return (int64_t)nida_get(&s, index);
}

int64_t Nida_str_ord0(Nida_Str s)
{
  if (s.data == NULL || s.length == 0)
    return 0;

  return (int64_t)nida_get(&s, 0);
}

char *Nida_str_to_utf8(Nida_Str s, size_t *out_len)
{
  if (s.data == NULL)
  {
    char *empty = calloc(1, 1);
    if (out_len != NULL)
      *out_len = 0;
    return empty;
  }

  if (s.length > (SIZE_MAX - 1) / 4)
  {
    if (out_len != NULL)
      *out_len = 0;
    return NULL;
  }

  size_t capacity = s.length * 4 + 1;
  char *buffer = malloc(capacity);
  if (buffer == NULL)
  {
    if (out_len != NULL)
      *out_len = 0;
    return NULL;
  }

  size_t written = 0;

  for (size_t i = 0; i < s.length; i++)
  {
    char chunk[4];
    size_t size = nida_encode_one(nida_get(&s, i), chunk);

    memcpy(buffer + written, chunk, size);
    written += size;
  }

  buffer[written] = '\0';

  if (out_len != NULL)
    *out_len = written;

  return buffer;
}

void Nida_str_print(Nida_Str s)
{
  size_t len = 0;
  char *utf8 = Nida_str_to_utf8(s, &len);

  if (utf8 == NULL)
  {
    fputs("None", stdout);
    return;
  }

  fwrite(utf8, 1, len, stdout);
  free(utf8);
}
