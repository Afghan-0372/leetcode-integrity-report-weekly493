#include <string>
#include <vector>

static std::string res_buf;

extern "C" {
    __declspec(dllexport) const char* get_ast_fingerprint_native(const char* input) {
        if (!input) return "";
        std::string s(input);
        res_buf.clear();
        res_buf.reserve(s.size() / 5);

        for (size_t i = 0; i < s.size(); ++i) {
            // Skip comments
            if (s[i] == '#') {
                while (i < s.size() && s[i] != '\n') i++;
                continue;
            }
            // skip strings
            if (s[i] == '"' || s[i] == '\'') {
                char quote = s[i];
                i++;
                while (i < s.size() && s[i] != quote) {
                    if (s[i] == '\\') i++;
                    i++;
                }
                continue;
            }

            if (s[i] == '(') { res_buf += "Call|"; continue; }
            if (s[i] == '[') { res_buf += "Subscript|"; continue; }

            if (strchr("+-*/%", s[i])) {
                res_buf += "BinOp|";
                if (i + 1 < s.size() && strchr("+-*/%", s[i+1])) i++;
                continue;
            }

            // keywords
            if ((i == 0 || !isalnum(s[i-1])) && isalpha(s[i])) {
                std::string word;
                while (i < s.size() && isalnum(s[i])) word += s[i++];
                i--; 
                if (word == "for") res_buf += "For|";
                else if (word == "while") res_buf += "While|";
                else if (word == "if") res_buf += "If|";
            }
        }
        if (!res_buf.empty()) res_buf.pop_back();
        return res_buf.c_str();
    }
}
