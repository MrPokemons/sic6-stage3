import os

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "prompt")

with (
    open(os.path.join(PROMPT_DIR, "base.md"), "r", encoding="utf8") as fbase,
    open(os.path.join(PROMPT_DIR, "scope.md"), "r", encoding="utf8") as fscope,
    open(os.path.join(PROMPT_DIR, "guideline.md"), "r", encoding="utf8") as fguideline,
    open(
        os.path.join(PROMPT_DIR, "generate-questions.md"), "r", encoding="utf8"
    ) as fgenerate_question,
    open(
        os.path.join(PROMPT_DIR, "verify-answer.md"), "r", encoding="utf8"
    ) as fverify_answer,
):
    BASE_PROMPT: str = fbase.read()
    SCOPE_PROMPT: str = fscope.read()
    GUIDELINE_PROMPT: str = fguideline.read()
    GENERATE_QUESTION_PROMPT: str = fgenerate_question.read()
    VERIFY_ANSWER_PROMPT: str = fverify_answer.read()
