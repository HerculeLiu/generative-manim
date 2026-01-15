import requests
from typing import Dict, Any

class Videos:
    """
    Handle video-related operations with the Animo API.
    """
    
    def __init__(self, client):
        self.client = client

    def create(
        self, 
        code: str, 
        file_class: str = "GenScene",
        aspect_ratio: str = "16:9",
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Create a video by rendering Manim code.

        Args:
            code (str): The Manim Python code to render
            file_class (str, optional): The Manim scene class name. Defaults to "GenScene"
            aspect_ratio (str, optional): Video aspect ratio ("16:9", "1:1", "9:16"). Defaults to "16:9"
            stream (bool, optional): Whether to stream the rendering progress. Defaults to False

        Returns:
            Dict[str, Any]: The API response containing the video URL
        """
        response = requests.post(
            f"{self.client.base_url}/v1/video/rendering",
            headers={
                "Authorization": f"Bearer {self.client.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "code": code,
                "file_class": file_class,
                "aspect_ratio": aspect_ratio,
                "stream": stream
            }
        )
        response.raise_for_status()
        return response.json()

    def generate(
        self,
        prompt: str,
        engine: str = "deepseek",
        model: str = "deepseek-chat"
    ) -> Dict[str, Any]:
        """
        Generate a video from a text prompt using AI.

        Args:
            prompt (str): The text prompt describing the animation to create
            engine (str, optional): The AI engine to use. Defaults to "anthropic"
            model (str, optional): The AI model to use. Defaults to "claude-3-7-sonnet-20250219"

        Returns:
            Dict[str, Any]: The API response containing the request ID and status
        """
        response = requests.post(
            f"{self.client.base_url}/v1/video/generation",
            headers={
                "Authorization": f"Bearer {self.client.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "prompt": prompt,
                "engine": engine,
                "model": model
            }
        )
        response.raise_for_status()
        return response.json()

    def retrieve(self, request_id: str) -> Dict[str, Any]:
        """
        Retrieve the status and result of a video generation request.

        Args:
            request_id (str): The ID of the generation request to check

        Returns:
            Dict[str, Any]: The API response containing the status and video URL if completed
        """
        response = requests.get(
            f"{self.client.base_url}/v1/video/generation/status/{request_id}",
            headers={
                "Authorization": f"Bearer {self.client.api_key}",
                "Content-Type": "application/json"
            }
        )
        response.raise_for_status()
        return response.json()

    def export(self, scenes: list, title_slug: str) -> Dict[str, Any]:
        """
        Export multiple scenes into a single video.

        Args:
            scenes (list): List of scene objects containing videoUrl
            title_slug (str): Slug for the exported video title

        Returns:
            Dict[str, Any]: The API response containing the exported video URL
        """
        response = requests.post(
            f"{self.client.base_url}/v1/video/exporting",
            headers={
                "Authorization": f"Bearer {self.client.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "scenes": scenes,
                "titleSlug": title_slug
            }
        )
        response.raise_for_status()
        return response.json() 
