#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include "Nida_core.h"
#include "print.h"

Nida_Str Nida_input(Nida_Str prompt)
{
  _Nida_print_a1(prompt, false);
  size_t len = 0;
  size_t capacity = 64;
  char *buffer = malloc(capacity);

  if (buffer == NULL)
    return (Nida_Str){.data = NULL, .length = 0};

  int ch;

  while ((ch = getchar()) != EOF && ch != '\n')
  {
    if (len + 1 >= capacity)
    {
      if (capacity > SIZE_MAX / 2)
      {
        free(buffer);
        return (Nida_Str){.data = NULL, .length = 0};
      }

      size_t new_capacity = capacity * 2;
      char *new_buffer = realloc(buffer, new_capacity);

      if (new_buffer == NULL)
      {
        free(buffer);
        return (Nida_Str){.data = NULL, .length = 0};
      }

      buffer = new_buffer;
      capacity = new_capacity;
    }

    buffer[len++] = (char)ch;
  }

  if (ch == EOF && len == 0)
  {
    free(buffer);
    return (Nida_Str){.data = NULL, .length = 0};
  }

  buffer[len] = '\0';

  Nida_Str result = Nida_str_from_utf8(buffer, len);
  free(buffer);

  return result;
}