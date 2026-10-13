"""scripts/ai_score.py run / extract / pilot, against a stand-in for the Claude API (no key,
no network). Checks the calls it makes, the files it writes, and that a second run sends
nothing already answered."""
import json
import os
import sys
from types import SimpleNamespace

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))

import ai_check  # noqa: E402
import ai_score  # noqa: E402
from test_ai_score import clean_claims  # noqa: E402


def usage(i, o):
    return SimpleNamespace(input_tokens=i, output_tokens=o, cache_creation_input_tokens=0, cache_read_input_tokens=0)


class FakeStream:
    def __init__(self, message):
        self.message = message

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self.message


class FakeClient:
    """Answers every prompt with a short reading that quotes its end marker; extracts claims
    that are all true, from the truth file of the pilot case with that marker."""

    def __init__(self, build):
        self.build, self.answer_calls, self.extract_calls = build, [], []
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))
        self.messages = SimpleNamespace(create=self._create)

    def _stream(self, **kw):
        self.answer_calls.append(kw)
        marker = kw["messages"][0]["content"].rstrip().rsplit("\n", 1)[-1]
        text = f"The prompt was complete ({marker}).\n\n5. Plain-language recap\nTake your time.\n"
        return FakeStream(SimpleNamespace(model=kw["model"], stop_reason="end_turn", usage=usage(10_000, 3_000),
                                          content=[SimpleNamespace(type="text", text=text)]))

    def _create(self, **kw):
        self.extract_calls.append(kw)
        content = kw["messages"][0]["content"]
        # The answer quotes the prompt's end marker, which names the spread's position count.
        case = next((c["id"] for c in self.cases() if self.truth(c["id"])["end_marker"] in content),
                    self.cases()[0]["id"])
        claims = clean_claims(self.truth(case))
        return SimpleNamespace(stop_reason="end_turn", usage=usage(2_000, 1_000),
                               content=[SimpleNamespace(type="text", text=json.dumps(claims))])

    def cases(self):
        with open(os.path.join(self.build, "cases.json")) as f:
            return [c for c in json.load(f) if c["variant"] == "full" and c["seed"] == ai_score.PILOT_SEED]

    def truth(self, case_id):
        with open(os.path.join(self.build, "truth", f"{case_id}.json"), encoding="utf-8") as f:
            return json.load(f)


def test_pilot_answers_extracts_and_scores(tmp_path, capsys):
    out = str(tmp_path)
    build = os.path.join(out, "build")
    ai_check.build(build)
    client = FakeClient(build)
    ai_score.pilot(client, out)

    answers = os.path.join(out, "answers")
    assert len(client.answer_calls) == len(ai_check.SPREAD_KEYS) * ai_score.PILOT_RUNS == 10
    call = client.answer_calls[0]
    assert call["model"] == "claude-opus-5-5" and call["fallbacks"] == "default"
    assert call["output_config"] == {"effort": "medium"} and "system" not in call
    with open(os.path.join(build, "prompts", "s408850_sp1_full.md"), encoding="utf-8") as f:
        assert call["messages"] == [{"role": "user", "content": f.read()}]

    names = sorted(os.listdir(answers))
    assert "s408850_sp12_full__opus-5-5__2.md" in names and "results.md" in names
    assert sum(n.endswith(".score.json") for n in names) == 10
    with open(os.path.join(answers, "s408850_sp3_full__opus-5-5__1.meta.json")) as f:
        meta = json.load(f)
    assert meta["served_model"] == "claude-opus-5-5" and meta["cost_usd"] == round((10_000 * 4 + 3_000 * 20) / 1e6, 4)
    with open(os.path.join(answers, "s408850_sp9_full__opus-5-5__1.score.json")) as f:
        assert json.load(f)["hard_errors"] == 0
    assert "This run cost about $1.14" in capsys.readouterr().out    # 10 x $0.10 answers + 10 x $0.014 claims

    # Again: nothing new to send.
    ai_score.pilot(client, out)
    assert len(client.answer_calls) == 10 and len(client.extract_calls) == 10
    # Extract again after the instructions change: every answer, no new answers.
    ai_score.extract(client, build, answers, again=True)
    assert len(client.answer_calls) == 10 and len(client.extract_calls) == 20


def test_refusal_saves_no_answer(tmp_path):
    build = os.path.join(str(tmp_path), "build")
    ai_check.build(build)
    client = FakeClient(build)
    refused = SimpleNamespace(model="claude-opus-5-5", stop_reason="refusal", usage=usage(10, 0), content=[])
    client.beta.messages.stream = lambda **kw: FakeStream(refused)
    answers = os.path.join(str(tmp_path), "answers")
    ai_score.run(client, build, answers, ["s408850_sp1_full"])
    assert os.listdir(answers) == ["s408850_sp1_full__opus-5-5__1.meta.json"]


def test_round_asks_first_then_answers_every_prompt_with_each_model(tmp_path, capsys):
    out = str(tmp_path)
    build = os.path.join(out, "build")
    ai_check.build(build)
    client = FakeClient(build)
    assert ai_score.full_round(client, out, ask=lambda q: "n") == 0.0
    assert client.answer_calls == [] and "Nothing sent." in capsys.readouterr().out

    questions = []
    ai_score.full_round(client, out, models=("claude-opus-5-5", "claude-haiku-5-5"),
                        ask=lambda q: questions.append(q) or "y")
    assert "roughly $" in questions[0]
    with open(os.path.join(build, "cases.json")) as f:
        cases = json.load(f)
    per_model = sum(2 if c["variant"] == "full" else 1 for c in cases)
    assert per_model == 56 and len(client.answer_calls) == 2 * per_model
    opus = [c for c in client.answer_calls if c["model"] == "claude-opus-5-5"]
    haiku = [c for c in client.answer_calls if c["model"] == "claude-haiku-5-5"]
    assert all(c["output_config"] == {"effort": "medium"} for c in opus)
    assert haiku and all("output_config" not in c for c in haiku)
    names = os.listdir(os.path.join(out, "answers"))
    assert sum(n.endswith(".score.json") for n in names) == 112
    assert "s408850_sp12_cut40__haiku-5-5__1.md" in names and "s408850_sp12_cut40__haiku-5-5__2.md" not in names

    # Nothing left to send: the estimate is nothing and no call is made.
    assert ai_score.round_estimate(build, os.path.join(out, "answers"), ("claude-opus-5-5", "claude-haiku-5-5")) == 0
