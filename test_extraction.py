from app import extract_questions

qs = extract_questions('uploads/sampledoctest.docx')
print(f'\n✓ SUCCESS: Extracted {len(qs)} questions\n')

# Show some samples
print("SAMPLE QUESTIONS:")
print(f"\nQ1 (MCQ):")
print(f"  Question: {qs[0]['question'][:60]}...")
print(f"  Type: {qs[0]['type']}")
print(f"  Correct Answer: {qs[0]['correct_answer']}\n")

print(f"Q2 (Fill-blank):")
print(f"  Question: {qs[1]['question'][:60]}...")
print(f"  Type: {qs[1]['type']}")
print(f"  Correct Answer: {qs[1]['correct_answer']}\n")

print(f"Q3 (True/False):")
print(f"  Question: {qs[2]['question'][:60]}...")
print(f"  Type: {qs[2]['type']}")
print(f"  Correct Answer: {qs[2]['correct_answer']}\n")

# Count types
mcqs = sum(1 for q in qs if q['type'] == 'mcq')
tfs = sum(1 for q in qs if q['type'] == 'true_false')
fills = sum(1 for q in qs if q['type'] == 'fill_blank')
descs = sum(1 for q in qs if q['type'] == 'descriptive')

print(f"\nCOUNT BY TYPE:")
print(f"  MCQ: {mcqs}")
print(f"  True/False: {tfs}")
print(f"  Fill-blank: {fills}")
print(f"  Descriptive/SQL: {descs}")
print(f"  TOTAL: {mcqs + tfs + fills + descs}\n")

