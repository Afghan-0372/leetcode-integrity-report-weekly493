#include <string.h>
#include <stdbool.h>

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#endif

EXPORT bool detect_ai_c(const char *code) {
    int score = 0;
    const char *patterns[] = {
        "if not nums: return 0",
        "len_nums = len(nums)",
        "# initialize variables",
        "float('-inf')"
    };

    for (int i = 0; i < 4; i++) {
        if (strstr(code, patterns[i]) != NULL) {
            score++;
            if (score >= 2) return true;
        }
    }
    return false;
}
