#ifndef NIDA_CORE_H
#define NIDA_CORE_H

#include <stdint.h>

#include "Nida_str.h"

#define NIDA_NONE_ADDR ((void *)(uintptr_t)0xDEADBEEFCAFE0000ULL)
static const void *Nida_None = NIDA_NONE_ADDR;

#endif // NIDA_CORE_H
