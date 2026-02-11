/*
 * =================================================================
 * ALPHA SOVEREIGN ORGANISM - SHARED MEMORY FORENSIC INSPECTOR
 * =================================================================
 * File: tools/debugger/shm_inspector.c
 * Status: PRODUCTION (Low-Level Diagnostic)
 * Pillar: Observability (الركيزة: المراقبة والتشخيص)
 * Forensic Purpose: فتح الذاكرة المشتركة وعرض محتوياتها (Hex Dump) للتأكد من سلامة البيانات المنقولة.
 * =================================================================
 */

#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>

// حجم العرض الافتراضي (عرض 16 بايت في السطر)
#define HEX_WIDTH 16

void print_hex_dump(const void *data, size_t size) {
    const unsigned char *p = (const unsigned char *)data;
    for (size_t i = 0; i < size; i += HEX_WIDTH) {
        // طباعة العنوان (Offset)
        printf("%08zx  ", i);

        // طباعة القيم الست عشرية (Hex)
        for (size_t j = 0; j < HEX_WIDTH; ++j) {
            if (i + j < size)
                printf("%02x ", p[i + j]);
            else
                printf("   ");
        }

        printf(" |");

        // طباعة القيم النصية (ASCII) إذا كانت قابلة للقراءة
        for (size_t j = 0; j < HEX_WIDTH; ++j) {
            if (i + j < size) {
                unsigned char c = p[i + j];
                printf("%c", (c >= 32 && c <= 126) ? c : '.');
            }
        }
        printf("|\n");
    }
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <shm_name> [size_to_read]\n", argv[0]);
        fprintf(stderr, "Example: %s /alpha_shm_market_tick 1024\n", argv[0]);
        return 1;
    }

    const char *shm_name = argv[1];
    size_t map_size = 4096; // حجم افتراضي صفحة واحدة
    if (argc >= 3) {
        map_size = atoll(argv[2]);
    }

    printf("[*] Inspecting Shared Memory: %s\n", shm_name);
    printf("[*] Target Size: %zu bytes\n", map_size);

    // 1. فتح كائن الذاكرة المشتركة (Read Only)
    int fd = shm_open(shm_name, O_RDONLY, 0666);
    if (fd == -1) {
        fprintf(stderr, "[!] Error opening SHM: %s\n", strerror(errno));
        return 1;
    }

    // 2. تعيين الذاكرة (Memory Mapping)
    void *ptr = mmap(0, map_size, PROT_READ, MAP_SHARED, fd, 0);
    if (ptr == MAP_FAILED) {
        fprintf(stderr, "[!] Error mapping memory: %s\n", strerror(errno));
        close(fd);
        return 1;
    }

    // 3. عرض البيانات (Forensic Dump)
    printf("-----------------------------------------------------------------\n");
    print_hex_dump(ptr, map_size);
    printf("-----------------------------------------------------------------\n");

    // 4. التنظيف
    munmap(ptr, map_size);
    close(fd);

    return 0;
}