from flask import Blueprint, jsonify, request
import anthropic
import os
from openai import OpenAI

code_generation_bp = Blueprint('code_generation', __name__)

def strip_thinking(text: str) -> str:
    if not text:
        return text
    while "<think>" in text and "</think>" in text:
        start = text.find("<think>")
        end = text.find("</think>", start)
        text = text[:start] + text[end + len("</think>") :]
    return text.strip()

@code_generation_bp.route('/v1/code/generation', methods=['POST'])
def generate_code():
    body = request.json
    prompt_content = body.get("prompt", "")
    model = body.get("model", "deepseek-reasoner")

    general_system_prompt = """
You are an assistant that writes Manim code for a single scene.

The following is an example of the code:
\`\`\`
from manim import *
from math import *

class GenScene(Scene):
    def construct(self):
        c = Circle(color=BLUE)
        self.play(Create(c))
\`\`\`

# Rules
1. Always use GenScene as the class name.
2. Use self.play() for all visible changes and animations.
3. Output only valid Python code, no explanations and no code fences.
4. Do not invent extra objects or steps beyond the user's prompt.
5. If the prompt implies the same objects are reused, reuse the same objects instead of creating new ones.
6. If elements should be removed/hidden, explicitly animate their removal (e.g., FadeOut).
7. Only use manim and math imports; no external libraries.
8. Before writing code, internally derive a clear action plan: list objects, then list step-by-step transformations; the code must follow that plan.
9. If the prompt is ambiguous, prefer continuous transformations of existing objects over creating new objects or resetting the scene.
10. Rotation direction must be explicit: clockwise uses a negative angle (e.g., -PI/2), counterclockwise uses a positive angle.
11. Preserve object scale: when segments form a polygon, do not scale or stretch them; keep segment lengths consistent with the original line.
12. Do not apply scaling or morphing unless the prompt explicitly requests it. Default transformations should be only move, rotate, or flip.
13. Frame usage: main objects should occupy roughly 60–75% of the frame width/height unless the prompt specifies otherwise.
14. Use only Manim-defined color constants (e.g., BLUE, BLUE_A, BLUE_B, BLUE_C, BLUE_D, BLUE_E, GREEN, RED). Do not invent color names.
    """

    if model.startswith("claude-"):
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        messages = [{"role": "user", "content": prompt_content}]
        try:
            response = client.messages.create(
                model=model,
                max_tokens=1000,
                temperature=0.1,
                system=general_system_prompt,
                messages=messages,
            )

            # Extract the text content from the response
            code = strip_thinking("".join(block.text for block in response.content))

            return jsonify({"code": code})

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    else:
        client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
        messages = [
            {"role": "system", "content": general_system_prompt},
            {"role": "user", "content": prompt_content},
        ]

        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1,
            )

            code = strip_thinking(response.choices[0].message.content or "")

            return jsonify({"code": code})

        except Exception as e:
            return jsonify({"error": str(e)}), 500
