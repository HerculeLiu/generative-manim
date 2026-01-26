from flask import Blueprint, jsonify, request
import anthropic
import os
import json
import subprocess
import uuid
from openai import OpenAI

video_generation_bp = Blueprint('video_generation', __name__)

CODE_GENERATION_SYSTEM_PROMPT = """
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
13. Frame usage: main objects should occupy roughly 70–85% of the frame width/height unless the prompt specifies otherwise.
14. Use only Manim-defined color constants (e.g., BLUE, BLUE_A, BLUE_B, BLUE_C, BLUE_D, BLUE_E, GREEN, RED). Do not invent color names.
15. If you add updaters: Scene.add_updater expects updater(dt); Mobject.add_updater expects updater(mobject, dt). Always include dt in the function signature.
16. Do not use self.camera.frame unless using MovingCameraScene. Use config.frame_width/frame_height or self.camera.frame_width/frame_height instead.
17. Scene does not support add_updater; attach updaters to a Mobject (or a hidden driver Mobject) and remove them from that same Mobject.
"""

def strip_code_fences(code: str) -> str:
    if not code:
        return code
    lines = code.splitlines()
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

def get_frame_config(aspect_ratio):
    if aspect_ratio == "16:9":
        return (3840, 2160), 14.22
    elif aspect_ratio == "9:16":
        return (1080, 1920), 8.0
    elif aspect_ratio == "1:1":
        return (1080, 1080), 8.0
    else:
        return (3840, 2160), 14.22


def generate_manim_code(prompt, engine="openai", model="deepseek-chat"):
    """Generate Manim code from a text prompt"""
    if model.startswith("claude-"):
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        messages = [{"role": "user", "content": prompt}]
        try:
            response = client.messages.create(
                model=model,
                max_tokens=1000,
                temperature=0.1,
                system=CODE_GENERATION_SYSTEM_PROMPT,
                messages=messages,
            )
            code = strip_thinking("".join(block.text for block in response.content))
            return code
        except Exception as e:
            raise Exception(f"Error generating code with {model}: {str(e)}")
    else:
        client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
        messages = [
            {"role": "system", "content": CODE_GENERATION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1,
            )
            code = strip_thinking(response.choices[0].message.content or "")
            return code
        except Exception as e:
            raise Exception(f"Error generating code with {model}: {str(e)}")


@video_generation_bp.route("/v1/video/generation", methods=["POST"])
def generate_video():
    """
    Generate a video from a text prompt.

    Request Body:
    {
        "prompt": "Create a Manim animation that shows a square transforming into a circle",
        "engine": "openai",  // Optional, defaults to "openai"
        "model": "gpt-4o",  // Optional, defaults to "gpt-4o"
        "aspect_ratio": "16:9",  // Optional, defaults to "16:9"
        "user_id": "user-123",  // Optional
        "project_name": "my-project",  // Optional
        "iteration": 1  // Optional
    }
    """
    try:
        # Extract parameters
        prompt = request.json.get("prompt")
        engine = request.json.get("engine", "openai")
        model = request.json.get("model", "deepseek-reasoner")
        aspect_ratio = request.json.get("aspect_ratio", "16:9")
        user_id = request.json.get("user_id") or str(uuid.uuid4())
        project_name = request.json.get("project_name", "untitled")
        iteration = request.json.get("iteration", 1)

        # Validate prompt
        if not prompt:
            return jsonify({"error": "A 'prompt' must be provided"}), 400

        print(f"Generating video from prompt: {prompt}")

        # Step 1: Generate Manim code
        print(f"Step 1: Generating Manim code using {engine}/{model}")
        try:
            code = strip_code_fences(generate_manim_code(prompt, engine, model))
            print(f"Code generation successful")
        except Exception as e:
            return jsonify({"error": f"Code generation failed: {str(e)}"}), 500

        # Step 2: Render the video
        print(f"Step 2: Rendering video")
        try:
            # Prepare the code with frame configuration
            frame_size, frame_width = get_frame_config(aspect_ratio)
            modified_code = f"""
from manim import *
from math import *
config.frame_size = {frame_size}
config.frame_width = {frame_width}

{code}
            """

            # Create a temporary file for the code
            file_name = f"scene_{os.urandom(2).hex()}.py"
            api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            public_dir = os.path.join(api_dir, "public")
            os.makedirs(public_dir, exist_ok=True)
            file_path = os.path.join(public_dir, file_name)

            with open(file_path, "w") as f:
                f.write(modified_code)

            # Run Manim to render the video
            command = [
                "manim",
                file_path,
                "GenScene",
                "--format=mp4",
                "--media_dir",
                ".",
                "--custom_folders",
            ]

            result = subprocess.run(
                command,
                cwd=os.path.dirname(os.path.realpath(__file__)),
                capture_output=True,
                text=True,
                timeout=900
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                return jsonify({"error": f"Manim rendering failed: {error_msg}"}), 500

            # Find the generated video file
            video_file_path = os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "GenScene.mp4"
            )

            if not os.path.exists(video_file_path):
                return jsonify({"error": "Video file not found after rendering"}), 500

            # Move video to public folder
            video_storage_file_name = f"video-{user_id}-{project_name}-{iteration}"
            new_file_name = f"{video_storage_file_name}.mp4"
            new_file_path = os.path.join(public_dir, new_file_name)

            import shutil
            shutil.move(video_file_path, new_file_path)

            # Generate the video URL
            base_url = request.host_url.rstrip('/') if request.host_url else os.getenv("BASE_URL", "http://127.0.0.1:8080")
            video_url = f"{base_url}/public/{new_file_name}"

            print(f"Video generated successfully: {video_url}")

            return jsonify({
                "message": "Video generated successfully",
                "video_url": video_url,
                "code": code
            }), 200

        except subprocess.TimeoutExpired:
            return jsonify({"error": "Video rendering timed out"}), 500
        except Exception as e:
            return jsonify({"error": f"Video rendering failed: {str(e)}"}), 500
        finally:
            # Cleanup temporary files
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                if os.path.exists(video_file_path):
                    os.remove(video_file_path)
            except:
                pass

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500
