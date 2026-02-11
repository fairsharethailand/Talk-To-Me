import streamlit as st
from gtts import gTTS
import base64, os, uuid, random

# --- Initial Setup ---
st.set_page_config(page_title="TPRS Magic Wheel V58.4", layout="wide")
if 'display_text' not in st.session_state: st.session_state.display_text = ""
if 'audio_key' not in st.session_state: st.session_state.audio_key = 0

# --- Grammar Database ---
PAST_TO_INF = {"went": "go", "ate": "eat", "saw": "see", "bought": "buy", "had": "have", "did": "do", "drank": "drink", "slept": "sleep", "wrote": "write", "came": "come", "ran": "run", "met": "meet", "spoke": "speak", "took": "take", "found": "find", "gave": "give", "thought": "think", "brought": "bring", "told": "tell", "made": "make", "cut": "cut", "put": "put", "hit": "hit", "read": "read", "cost": "cost"}
IRREGULAR_PLURALS = ["children", "people", "men", "women", "mice", "teeth", "feet", "geese", "oxen"]

# --- Core Functions ---
def check_tense(pred):
    w = pred.split()
    if not w: return "unknown"
    v = w[0].lower().strip()
    if v.endswith("ed") or v in PAST_TO_INF: return "past"
    return "present"

def conjugate_singular(pred):
    w = pred.split(); v = w[0].lower(); rest = " ".join(w[1:])
    if v.endswith('s') or check_tense(v) == "past": return pred
    if v.endswith(('ch', 'sh', 'x', 's', 'z', 'o')): v += "es"
    elif v.endswith('y') and len(v) > 1 and v[-2] not in 'aeiou': v = v[:-1] + "ies"
    else: v += "s"
    return f"{v} {rest}".strip()

def get_aux(subj, p1, p2):
    if check_tense(p1) == "past" or check_tense(p2) == "past": return "Did"
    s = subj.lower().strip()
    if s in IRREGULAR_PLURALS or 'and' in s or s in ['i', 'you', 'we', 'they'] or (s.endswith('s') and s not in ['james', 'charles', 'boss']): return "Do"
    return "Does"

def to_inf(pred, other):
    w = pred.split(); v = w[0].lower(); rest = " ".join(w[1:])
    if check_tense(pred) == "past" or check_tense(other) == "past" or v in ['had', 'has', 'have']:
        if v in ['had', 'has', 'have']: inf = "have"
        elif v in PAST_TO_INF: inf = PAST_TO_INF[v]
        elif v.endswith("ied"): inf = v[:-3] + "y"
        elif v.endswith("ed"): inf = v[:-2]
        else: inf = v
    else:
        if v.endswith("es"): inf = v[:-2]
        elif v.endswith("s") and not v.endswith("ss"): inf = v[:-1]
        else: inf = v
    return f"{inf} {rest}".strip()

def build_logic(q_type, d):
    s1, p1, s2, p2 = d['s1'], d['p1'], d['s2'], d['p2']
    subj_r, pred_r = (s1 or "He"), (p1 or "is here")
    subj_t = s2 if s2 != "-" else s1
    pred_t = p2 if p2 != "-" else p1
    be_verbs = ['is', 'am', 'are', 'was', 'were', 'can', 'will', 'must']

    def is_be(p): return p.lower().split() and p.lower().split()[0] in be_verbs
    def swap(s, p): 
        pts = p.split()
        return f"{pts[0].capitalize()} {s} {' '.join(pts[1:])}".strip()

    if q_type == "Statement": return d['main_sent']
    if q_type == "Negative":
        if is_be(pred_t): return f"No, {subj_t} {pred_t.split()[0]} not {' '.join(pred_t.split()[1:])}."
        return f"No, {subj_t} {get_aux(subj_t, pred_t, pred_r).lower()} not {to_inf(pred_t, pred_r)}."
    if q_type == "Yes-Q":
        if is_be(pred_r): return swap(subj_r, pred_r) + "?"
        return f"{get_aux(subj_r, pred_r, pred_t)} {subj_r} {to_inf(pred_r, pred_t)}?"
    if q_type == "No-Q":
        if is_be(pred_t): return swap(subj_t, pred_t) + "?"
        return f"{get_aux(subj_t, pred_t, pred_r)} {subj_t} {to_inf(pred_t, pred_r)}?"
    if q_type == "Who":
        v = pred_r.lower().split()[0]
        rest = " ".join(pred_r.split()[1:])
        if v in ['am', 'are']: return f"Who is {rest}?"
        if v == 'were': return f"Who was {rest}?"
        if not is_be(pred_r): return f"Who {conjugate_singular(pred_r)}?"
        return f"Who {pred_r}?"
    if q_type in ["What", "Where", "When", "How", "Why"]:
        if is_be(pred_r): return f"{q_type} {pred_r.split()[0]} {subj_r} {' '.join(pred_r.split()[1:])}?"
        return f"{q_type} {get_aux(subj_r, pred_r, pred_t).lower()} {subj_r} {to_inf(pred_r, pred_t)}?"
    return d['main_sent']

def play_voice(text):
    try:
        tts = gTTS(text=text, lang='en')
        fn = f"v_{uuid.uuid4()}.mp3"
        tts.save(fn)
        with open(fn, "rb") as f: b64 = base64.b64encode(f.read()).decode()
        st.session_state.audio_key += 1
        st.markdown(f'<audio autoplay key="{st.session_state.audio_key}"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
        os.remove(fn)
    except: pass

# --- UI Layout ---
st.title("🎡 TPRS Magic Wheel V58.4")
m_in = st.text_input("📝 Main Sentence", "The children eat the cake.")
c1, c2 = st.columns(2)
with c1:
    sr, pr = st.text_input("Subject (R):", "The children"), st.text_input("Predicate (R):", "eat the cake")
with c2:
    st_in, pt = st.text_input("Subject (T):", "-"), st.text_input("Predicate (T):", "eat the bread") 

if st.button("🎰 RANDOM TRICK", use_container_width=True, type="primary"):
    clicked = random.choice(["Statement", "Yes-Q", "No-Q", "Negative", "Who", "What", "Where", "When", "How", "Why"])
    res = build_logic(clicked, {'s1':sr, 'p1':pr, 's2':st_in, 'p2':pt, 'main_sent':m_in})
    st.session_state.display_text = f"🎯 {clicked}: {res}"
    play_voice(res)

if st.session_state.display_text: st.info(st.session_state.display_text)
