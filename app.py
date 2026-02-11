import streamlit as st
from gtts import gTTS
import base64
import os
import uuid
import random

# 1. ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="TPRS Magic Wheel V58.3 (Fixed Who)", layout="wide")

# 2. Session State
if 'display_text' not in st.session_state:
    st.session_state.display_text = ""
if 'audio_key' not in st.session_state:
    st.session_state.audio_key = 0

# --- Grammar Logic ---
PAST_TO_INF = {
    "went": "go", "ate": "eat", "saw": "see", "bought": "buy", 
    "had": "have", "did": "do", "drank": "drink", "slept": "sleep", 
    "wrote": "write", "came": "come", "ran": "run", "met": "meet",
    "spoke": "speak", "took": "take", "found": "find", "gave": "give",
    "thought": "think", "brought": "bring", "told": "tell", "made": "make",
    "cut": "cut", "put": "put", "hit": "hit", "read": "read", "cost": "cost"
}

def is_present_perfect(predicate):
    words = predicate.lower().split()
    if len(words) >= 2 and words[0] in ['have', 'has', 'had']:
        v2 = words[1]
        if v2.endswith('ed') or v2 in PAST_TO_INF or v2 in ['been', 'done', 'gone', 'seen', 'eaten']:
            return True
    return False

def check_tense_type(predicate):
    words = predicate.split()
    if not words: return "unknown"
    v = words[0].lower().strip()
    if v.endswith("ed") or v in PAST_TO_INF:
        return "past"
    if v.endswith("s") or v.endswith("es") or v in ["go", "eat", "see", "buy", "do", "drink", "sleep", "write", "come", "run", "meet", "speak", "take", "find", "give", "think", "bring", "tell", "make"]:
        return "present"
    return "unknown"

def conjugate_singular(predicate):
    """ฟังก์ชันพิเศษสำหรับ Who: แปลงกริยาเป็นรูปเติม s/es"""
    words = predicate.split()
    if not words: return ""
    v = words[0].lower(); rest = " ".join(words[1:])
    # ถ้าเป็นกริยาช่วยหรือเป็นอดีตแล้ว ไม่ต้องเปลี่ยน
    if v in ['is', 'was', 'has', 'can', 'will', 'must', 'should'] or check_tense_type(v) == "past":
        return predicate
    # กฎการเติม s/es
    if v.endswith(('ch', 'sh', 'x', 's', 'z', 'o')): v += "es"
    elif v.endswith('y') and len(v) > 1 and v[-2] not in 'aeiou': v = v[:-1] + "ies"
    else: v += "s"
    return f"{v} {rest}".strip()

def get_auxiliary(subject, pred_target, pred_other):
    if is_present_perfect(pred_target): return None 
    tense_target = check_tense_type(pred_target)
    tense_other = check_tense_type(pred_other)
    if tense_target == "past" or tense_other == "past": return "Did"
    s = subject.lower().strip()
    if 'and' in s or s in ['i', 'you', 'we', 'they'] or (s.endswith('s') and s not in ['james', 'charles', 'boss']):
        return "Do"
    return "Does"

def to_infinitive(predicate, other_predicate):
    words = predicate.split()
    if not words: return ""
    v = words[0].lower().strip(); rest = " ".join(words[1:])
    is_past = (check_tense_type(predicate) == "past" or check_tense_type(other_predicate) == "past")
    if is_past or v in ['had', 'has', 'have']:
        if v in ['had', 'has', 'have']: inf_v = "have"
        elif v in PAST_TO_INF: inf_v = PAST_TO_INF[v]
        elif v.endswith("ed"): inf_v = v[:-3] + "y" if v.endswith("ied") else v[:-2]
        else: inf_v = v
    else:
        if v.endswith("es"): inf_v = v[:-2]
        elif v.endswith("s") and not v.endswith("ss"): inf_v = v[:-1]
        else: inf_v = v
    return f"{inf_v} {rest}".strip()

def has_be_verb(predicate):
    v_low = predicate.lower().split()
    be_and_modals = ['is', 'am', 'are', 'was', 'were', 'can', 'will', 'must', 'should', 'could', 'would']
    return v_low and v_low[0] in be_and_modals

def build_logic(q_type, data):
    s1, p1, s2, p2 = data['s1'], data['p1'], data['s2'], data['p2']
    main_sent = data['main_sent']
    subj_real, pred_real = (s1 if s1 else "He"), (p1 if p1 else "is here")
    subj_trick = s2 if s2 != "-" else s1
    pred_trick = p2 if p2 != "-" else p1

    def swap_front(s, p):
        parts = p.split()
        return f"{parts[0].capitalize()} {s} {' '.join(parts[1:])}".strip()

    if q_type == "Statement": return main_sent
    if q_type == "Negative":
        if has_be_verb(pred_trick) or is_present_perfect(pred_trick):
            return f"No, {subj_trick} {pred_trick.split()[0]} not {' '.join(pred_trick.split()[1:])}."
        aux = get_auxiliary(subj_trick, pred_trick, pred_real)
        return f"No, {subj_trick} {aux.lower()} not {to_infinitive(pred_trick, pred_real)}."
    if q_type == "Yes-Q":
        if has_be_verb(pred_real) or is_present_perfect(pred_real): return swap_front(subj_real, pred_real) + "?"
        return f"{get_auxiliary(subj_real, pred_real, pred_trick)} {subj_real} {to_infinitive(pred_real, pred_trick)}?"
    if q_type == "No-Q":
        if has_be_verb(pred_trick) or is_present_perfect(pred_trick): return swap_front(subj_trick, pred_trick) + "?"
        return f"{get_auxiliary(subj_trick, pred_trick, pred_real)} {subj_trick} {to_infinitive(pred_trick, pred_real)}?"
    
    # --- WHO LOGIC (แก้ไขตามที่ต้องการ) ---
    if q_type == "Who":
        words = pred_real.split()
        if not words: return "Who?"
        v_orig = words[0].lower(); rest = " ".join(words[1:])
        if v_orig in ['am', 'are']: return f"Who is {rest}?"
        if v_orig == 'were': return f"Who was {rest}?"
        be_modals = ['is', 'was', 'has', 'can', 'will', 'must', 'should']
        if v_orig not in be_modals and check_tense_type(pred_real) != "past":
            return f"Who {conjugate_singular(pred_real)}?"
        return f"Who {pred_real}?"

    # --- WHAT, WHERE, etc. (คงเดิม) ---
    if q_type in ["What", "Where", "When", "How", "Why"]:
        if has_be_verb(pred_real) or is_present_perfect(pred_real):
            return f"{q_type} {pred_real.split()[0]} {subj_real} {' '.join(pred_real.split()[1:])}?"
        aux = get_auxiliary(subj_real, pred_real, pred_trick)
        return f"{q_type} {aux.lower()} {subj_real} {to_infinitive(pred_real, pred_trick)}?"
    
    if q_type == "Either/Or":
        if s2 != "-" and s1.lower().strip() != s2.lower().strip():
            if has_be_verb(pred_real) or is_present_perfect(pred_real):
                return f"{pred_real.split()[0].capitalize()} {subj_real} or {subj_trick} {' '.join(pred_real.split()[1:])}?"
            return f"{get_auxiliary(subj_real, pred_real, pred_trick)} {subj_real} or {subj_trick} {to_infinitive(pred_real, pred_trick)}?"
        else:
            p_alt = p2 if p2 != "-" else "something else"
            if has_be_verb(pred_real) or is_present_perfect(pred_real): return f"{swap_front(subj_real, pred_real)} or {p_alt}?"
            return f"{get_auxiliary(subj_real, pred_real, p_alt)} {subj_real} {to_infinitive(pred_real, p_alt)} or {to_infinitive(p_alt, pred_real)}?"
    return main_sent

def play_voice(text):
    if text:
        try:
            tts = gTTS(text=text.replace("🎯",""), lang='en')
            filename = f"voice_{uuid.uuid4()}.mp3"
            tts.save(filename)
            with open(filename, "rb") as f: b64 = base64.b64encode(f.read()).decode()
            st.session_state.audio_key += 1
            st.markdown(f'<audio autoplay key="{st.session_state.audio_key}"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
            os.remove(filename)
        except: pass

# --- UI ---
st.title("🎡 TPRS Magic Wheel V58.3 (Fixed Who)")
main_input = st.text_input("📝 Main Sentence", "The children eat the cake.")
col1, col2 = st.columns(2)
with col1:
    s_r = st.text_input("Subject (R):", "The children")
    p_r = st.text_input("Predicate (R):", "eat the cake")
with col2:
    s_t = st.text_input("Subject (T):", "-")
    p_t = st.text_input("Predicate (T):", "eat the bread") 

data_packet = {'s1':s_r, 'p1':p_r, 's2':s_t, 'p2':p_t, 'main_sent':main_input}
st.divider()

clicked_type = None
if st.button("🎰 RANDOM TRICK", use_container_width=True, type="primary"):
    clicked_type = random.choice(["Statement", "Yes-Q", "No-Q", "Negative", "Either/Or", "Who", "What", "Where", "When", "How", "Why"])

row1 = st.columns(5)
for i, (lbl, mode) in enumerate([("📢 Statement", "Statement"), ("✅ Yes-Q", "Yes-Q"), ("❌ No-Q", "No-Q"), ("🚫 Negative
