from flask import Blueprint, jsonify, request
import anthropic
import json
import os
from openai import OpenAI


story_split_bp = Blueprint("story_split", __name__)

SPLIT_SYSTEM_PROMPT = """
You are an expert storyboarder for Manim animations.
Given a full video script, split it into a sequence of scene prompts.

Guiding principle (apply everywhere): write with strong visual continuity. Every prompt must read like a clear, step-by-step storyboard with concrete visual actions and object movements.

Strict rules (must follow):
1) Each scene prompt must be fully self-contained and logically complete. It must NOT rely on any other scene.
2) Never reference or imply anything outside the current scene. Do not use phrases like "previous scene", "as before", "continue", "then next", "carry over", or comparative/carry-over language like "new", "longer", "again", "still", "now". If any of these appear, the output is invalid and must be rewritten.
3) If the script describes ONE long animation (even with multiple beats), keep it as ONE scene and describe the full progression in a single prompt. Do not split a single continuous animation into multiple scenes.
3a) Do NOT create a separate setup scene and a separate explanation scene when they use the same objects. Setup + explanation must be in the SAME prompt.
4) Every scene must start from a blank canvas and explicitly introduce every object it uses inside the same prompt. Begin each prompt with a sentence that introduces the initial objects on a blank canvas.
5) Avoid transitions that imply prior context (e.g., "fades out") unless that object was introduced earlier in the SAME prompt.
6) Preserve quantity and object continuity: if the script says "a line is divided into N segments and those segments form a polygon", the prompt must explicitly state that the SAME line is split into N segments and those exact segments are rearranged/connected to form the polygon (not a new, separate polygon).
7) When a transformation uses parts of an object, explicitly state "the same pieces" and keep the count consistent (e.g., 3 segments -> triangle, 4 -> square, 5 -> pentagon).
8) If a script segment contains a single coherent visual idea, keep it together as one scene and describe it as a continuous animation.
8a) Only split into multiple scenes if the script clearly shifts to a different visual setting or introduces a new, unrelated idea with different objects.
9) Maintain element consistency within a scene: reuse the SAME objects unless you explicitly replace/remove them.
10) After a transformation completes, explicitly remove or hide elements that are no longer needed to avoid clutter.
11) For temporary aids (arrows, highlights, plus signs, helper lines), explicitly hide/remove them after each micro-step if they are reused, so the scene stays clean.
12) Do not duplicate existing objects (numbers, labels, shapes). If something is already on screen, only highlight or annotate the existing instance.
13) Relationship markers must make visual sense: place the plus sign between the two addends, and draw arrows from each addend to the result (never from the plus sign).
14) Always translate the script into explicit visual actions before writing the prompt: list objects, then list step-by-step transformations. The final prompt must follow that action sequence.
15) If the script is ambiguous, prefer conservative object reuse and continuous transformations instead of creating new objects or resetting the scene.
16) Segment markers are temporary: remove them immediately after the split is shown and before the segments detach or form a polygon.
17) Preserve length and scale: when a line is split into segments and used to form a polygon, the SAME segments must be used without scaling or stretching. The polygon perimeter must match the original line length.
18) Do not apply scaling or shape-morphing unless the script explicitly requests it. Default transformations should be only move, rotate, or flip, and keep lengths/scale consistent. Use morphing (e.g., Transform) only when the script says a shape changes into another shape.

Output format requirements:
- Return ONLY valid JSON.
- The JSON must be a list of objects with a "prompt" field.
- The "prompt" must be a complete mini-script: what appears, how it transforms, and the end state.

Example:
[
  {
    "prompt": "In a single continuous animation, a blue square appears at center, rotates slightly, and morphs into a circle. The circle pulses once, then a label 'Area = ?' appears beneath it. After the pulse, remove the rotation guide lines and hide the label to keep the scene clean."
  },
  {
    "prompt": "On the screen, the numbers 1, 1, 2, 3, 5, 8, 13, 21 are displayed in a row. First, highlight the first two 1s and place a plus sign between them; next, highlight the 2, then insert an equals sign between the second 1 and the 2. After that, hide the plus and equals signs and remove the highlighting. Then highlight 2 and 3, place a plus sign between them, highlight 5, and insert an equals sign between 3 and 5. Continue this pattern."
  },
  {
    "prompt": "A single line appears at center. It is divided into three equal segments. Those same three segments detach and connect end-to-end to form a triangle. Without resetting the scene, the same line re-forms, is divided into four segments, and those same segments connect into a square. Remove the segment markers each time a polygon finishes to keep the scene clean."
  },
  {
    "prompt": "A line appears in the center of the screen and is divided evenly into three segments. Each endpoint is marked with a small yellow dot. The leftmost segment then rotates 120° clockwise about its right endpoint, while the rightmost segment rotates 120° counter-clockwise about its left endpoint. The endpoints move with their segments, and the three segments finally form a triangle. The yellow dots are then hidden."
  },
]
"""


def strip_code_fences(text: str) -> str:
    if not text:
        return text
    lines = text.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def strip_thinking(text: str) -> str:
    if not text:
        return text
    while "<think>" in text and "</think>" in text:
        start = text.find("<think>")
        end = text.find("</think>", start)
        text = text[:start] + text[end + len("</think>") :]
    return text.strip()


def parse_json_list(text: str):
    cleaned = strip_code_fences(strip_thinking(text))
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON list found in response.")
    return json.loads(cleaned[start : end + 1])




@story_split_bp.route("/v1/video/splitting", methods=["POST"])
def split_story():
    body = request.json or {}
    script = (body.get("script") or "").strip()
    engine = (body.get("engine") or "openai").strip()
    model = (body.get("model") or "deepseek-reasoner").strip()

    if not script:
        return jsonify({"error": "A 'script' must be provided"}), 400

    if model.startswith("claude-"):
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        messages = [{"role": "user", "content": script}]
        try:
            response = client.messages.create(
                model=model,
                max_tokens=1200,
                temperature=0.0,
                system=SPLIT_SYSTEM_PROMPT,
                messages=messages,
            )
            raw = "".join(block.text for block in response.content)
        except Exception as e:
            return jsonify({"error": f"Split generation failed: {str(e)}"}), 500
    else:
        client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
        messages = [
            {"role": "system", "content": SPLIT_SYSTEM_PROMPT},
            {"role": "user", "content": script},
        ]
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.0,
            )
            raw = response.choices[0].message.content or ""
        except Exception as e:
            return jsonify({"error": f"Split generation failed: {str(e)}"}), 500

    try:
        data = parse_json_list(raw)
    except Exception as e:
        return jsonify({"error": f"Invalid JSON from model: {str(e)}"}), 500

    prompts = []
    for item in data:
        if isinstance(item, dict) and item.get("prompt"):
            prompts.append({"prompt": item["prompt"]})

    if not prompts:
        return jsonify({"error": "No prompts returned from model"}), 500

    return jsonify({"scenes": prompts, "engine": engine, "model": model}), 200
