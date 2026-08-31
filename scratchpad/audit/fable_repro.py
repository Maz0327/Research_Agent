import json, sys
sys.path.insert(0, '.')
from backend.pipeline.briefing_gates import normalize, _quote_is_present, names_in
from backend.pipeline.text_similarity import statement_similarity, says_the_same_thing, content_tokens

doc0 = json.load(open('scratchpad/e2e_films/packer_r3_doc_0.json'))
# find raw texts
def texts(d):
    out=[]
    def walk(x):
        if isinstance(x,dict):
            for k,v in x.items():
                if k=='full_text' and isinstance(v,str): out.append(v)
                else: walk(v)
        elif isinstance(x,list):
            for i in x: walk(i)
    walk(d); return out
raw = texts(doc0)
print("sources with full_text:", len(raw), "chars:", sum(len(t) for t in raw))
corpus = normalize(" ".join(raw))

# 1. Invented names via substring
for name in ["Ted", "Rob", "Al", "Ann", "Marshal Ferguson", "Christopher Nolan"]:
    toks = names_in(name + " went to the mountains.")
    verdict = {t: (normalize(t) in corpus) for t in toks}
    print("NAME", name, "->", verdict)

# 2. Fabricated quote from corpus vocabulary
fakes = [
  '"Packer confessed that he killed the five men and ate their flesh in the mountains"',
  '"the miners were guilty and the court found Packer innocent of every charge that winter"',
]
for f in fakes:
    q = f.strip('"')
    print("QUOTE passes:", _quote_is_present(q, corpus), "|", q[:60])

# 3. Polarity
pairs = [
  ("Packer did not kill the five men in the mountains", "Packer killed the five men in the mountains"),
  ("Packer denied that he killed his companions for food", "Packer admitted that he killed his companions for food"),
  ("The jury found Packer not guilty of murder", "The jury found Packer guilty of murder"),
]
for a,b in pairs:
    print("SIM %.3f same=%s | %s // %s" % (statement_similarity(a,b), says_the_same_thing(a,b), a, b))

print("---- round 2: names mid-sentence ----")
for s in ["He met Ted at the camp.", "They hired Rob and Nick for the job.",
          "Sheriff Denver Lake spoke.", "A man named Grant Sanchez arrived."]:
    toks = names_in(s)
    print(s, "->", {t: (normalize(t) in corpus) for t in toks})

print("---- harvest dedup polarity ----")
from backend.pipeline.text_similarity import group_matching
items=[("F1","The jury found Packer guilty of murder"),
       ("F2","The jury found Packer not guilty of murder")]
print(group_matching(items))
