import re
import ctypes
import os

def load_lib(dll_name: str, fname, arg, res):
    try:
        dll_path = os.path.abspath(dll_name)
        lib = ctypes.CDLL(dll_path)
        # def the interface
        func = getattr(lib, fname)
        func.argtypes = arg
        func.restype = res
        print(f'{dll_name} - loaded')
        return func
    except Exception as e:
        print(f"DLL Not loaded: {e}")
        lib = None
lib = load_lib('libnoise.dll', 'detect_ai_c', [ctypes.c_char_p], ctypes.c_bool)
lib_ast = load_lib('fast_ast.dll', 'get_ast_fingerprint_native', [ctypes.c_char_p], ctypes.c_char_p)


def parse_dump(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"[-] Error: {file_path} not found.")
        return []

    # Compile pattern for block RANKS
    rank_pattern = re.compile(r"### RANK (\d+) ###\n(.*?)\n##################", re.DOTALL)
    rank_blocks = rank_pattern.findall(content*5) # u Can multiply by 10 to multiply data and check scalability
    
    parsed = []
    for rank, block in rank_blocks:
        for q_num in range(1, 5):
            q_pattern = rf"\[Q{q_num}_START\]\n(.*?)\n\[Q{q_num}_END\]"
            code_match = re.search(q_pattern, block, re.DOTALL)
            
            if code_match:
                code = code_match.group(1).strip()
                # FILTER SHORT CODES!!! IMPORTANT THING OF ALL SCRIPT!!!
                if len(code) > 40:
                    parsed.append({
                        "rank": int(rank), 
                        "q": f"Q{q_num}", 
                        "code": code
                    })
    return parsed

#============================
# PRE COMPILE FOR RE:
# RE LOGIC SIGNATURE
RE_COMMENTS = re.compile(r'//.*|/\*[\s\S]*?\*/')
RE_LOGIC = re.compile(r'(\.\w+\(|parent\[|size\[|edges\[|id\+\+|idCounter\+\+|\+1|\.sort\(|find\(|union\()')

#NORMALIZE
NO_COMMENTS_RE = re.compile(r'(#.*)|(/\*.*?\*/)')
CODE_RE1 = re.compile(r'"[^"]*"')
CODE_RE2 = re.compile(r'\b\d+\b')
CODE_RE3 = re.compile(r'\b[a-zA-Z_]\w*\b')
PARTS_CODE_RE = re.compile(r'\s+')
# Using set momentally search O(1)
KEYWORDS_SET = {"if", "else", "for", "while", "def", "return", "class", "import"} 

#================================

def normalize(code):
        code = NO_COMMENTS_RE.sub('', code)

        code = CODE_RE1.sub('"S"', code)
        code = CODE_RE2.sub('N', code)

        code = CODE_RE3.sub(lambda m: m.group(0) if m.group(0) in KEYWORDS_SET else 'V', code)

        parts = PARTS_CODE_RE.split(code) # Del space
        parts.sort()
        
        return "".join(parts).lower()

def get_logic_signature(code):
        code = RE_COMMENTS.sub('', code)
        important_calls = RE_LOGIC.findall(code)
        return "".join(important_calls)
#=================================
# GET AST
def get_ast_c(code: str) -> str:
    res = lib_ast(code.encode('utf-8'))
    return res.decode('utf-8')
    
#=================================================
###### NOISE AI

def detect_ai_noise_c(code: str) -> bool:
    if not lib: return False
    # transfer to lover and bytes for C 
    return lib(code.lower().encode('utf-8'))
