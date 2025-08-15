#!/usr/bin/env python3
"""
Ollama DJ - Uses Ollama to determine music genre based on activity
Alternative to llm_dj.py that works with Ollama instead of LM Studio
"""

import time
import sys
import requests
import argparse
import json
import base64
from io import BytesIO
from PIL import Image
import mss
from openai import OpenAI


def examine_activity(debug=False, monitor_index=0):
    """Take a screenshot of the current screen and return it as a base64 encoded string."""
    try:
        with mss.mss() as sct:
            # Take screenshot to share to the LLM
            # monitor_index 0 = all monitors combined, 1+ = specific monitor
            if monitor_index >= len(sct.monitors):
                print(f"   WARNING: Monitor {monitor_index} not found, using all monitors")
                monitor_index = 0
            
            monitor = sct.monitors[monitor_index]
            if monitor_index == 0:
                print(f"   Examining all monitors combined")
            else:
                print(f"   Examining monitor {monitor_index}")
            screenshot = sct.grab(monitor)
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            
            # Resize image to reduce file size (optional, but recommended for LLM processing)
            # Keep aspect ratio but limit max dimension to 1024px
            max_size = 1024
            if img.width > max_size or img.height > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            if debug:
                print("   DEBUG: Opening screenshot preview...")
                img.show()
            
            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return img_str
    except Exception as e:
        print(f"ERROR: Failed to take screenshot: {e}")
        return None


def get_genre_from_ollama(client, model_name, screenshot_b64):
    """Use Ollama to get music genre from screenshot."""
    try:
        print(f"-> Analyzing activity with Ollama model '{model_name}'...")
        
        # Request JSON output via optimized system prompt
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "### SYSTEM\nYou are given one image.\n\n### INSTRUCTION\n1. Silently infer what the user is doing in the screenshot.\n2. Pick one 1-2-word music genre that fits the activity.\n   *Think step-by-step internally only.*\n3. Return a JSON object that conforms to the provided schema.\n   **Do not output anything else.**\n\n### RESPONSE FORMAT\n{\"music_genre\": \"<genre>\"}"
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{screenshot_b64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=50,
            temperature=0.0
        )
        
        content = response.choices[0].message.content
        
        try:
            # First, strip any markdown code blocks that might wrap the JSON
            import re
            # Remove ```json and ``` markers
            cleaned_content = re.sub(r'^```(?:json)?\s*\n?', '', content.strip(), flags=re.MULTILINE)
            cleaned_content = re.sub(r'\n?```\s*$', '', cleaned_content, flags=re.MULTILINE)
            
            genre_data = json.loads(cleaned_content.strip())
            if "music_genre" in genre_data and isinstance(genre_data["music_genre"], str):
                return genre_data["music_genre"]
            else:
                print(f"   WARNING: 'music_genre' key missing or invalid in Ollama response: {content}")
                return None
        except json.JSONDecodeError:
            print(f"   WARNING: Could not parse JSON from Ollama response: {content}")
            # Try to find JSON-like pattern in the text as fallback
            import re
            match = re.search(r'\{"music_genre":\s*"([^"]+)"\}', content)
            if match:
                return match.group(1)
            return None
        
    except Exception as e:
        print(f"   ERROR: Failed to get genre from Ollama: {e}")
        return None


def change_server_genre(server_ip, server_port, genre):
    """Sends a POST request to the music server to change the genre."""
    url = f"http://{server_ip}:{server_port}/genre"
    payload = {"genre": genre}
    print(f"-> Attempting to change genre to '{genre}'...")
    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        print(f"   SUCCESS: Genre changed to '{response.json().get('genre', genre)}'.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"   ERROR: Could not connect to the music server at {url}. Details: {e}")
        return False


def check_ollama_connection(ollama_url, model_name):
    """Check if Ollama is running and the model is available."""
    try:
        # Check if Ollama is running
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        response.raise_for_status()
        
        # Check if the model is available
        models = response.json().get("models", [])
        model_names = [model.get("name", "") for model in models]
        
        if model_name not in model_names:
            print(f"   WARNING: Model '{model_name}' not found in Ollama.")
            print(f"   Available models: {', '.join(model_names)}")
            print(f"   You can pull the model with: ollama pull {model_name}")
            return False
        
        print(f"   SUCCESS: Ollama is running and model '{model_name}' is available.")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"   ERROR: Could not connect to Ollama at {ollama_url}. Details: {e}")
        print(f"   Make sure Ollama is running with: ollama serve")
        return False


def main(args):
    """Main loop to take screenshots, get genre suggestions, and update music."""
    ollama_url = f"http://{args.ollama_host}:{args.ollama_port}"
    
    print("--- Ollama DJ Starting ---")
    print(f"Screen Activity Analysis every {args.interval} seconds")
    print(f"Ollama URL: {ollama_url}")
    print(f"Ollama Model: {args.model}")
    print(f"Music Server: http://{args.music_ip}:{args.music_port}/genre")
    
    # Show monitor info
    try:
        with mss.mss() as sct:
            if args.monitor == 0:
                print(f"Monitor: All monitors combined")
            elif args.monitor < len(sct.monitors):
                monitor = sct.monitors[args.monitor]
                print(f"Monitor: Monitor {args.monitor} ({monitor['width']}x{monitor['height']})")
            else:
                print(f"Monitor: {args.monitor} (will fallback to all monitors)")
    except Exception as e:
        print(f"Monitor: Unable to detect monitor info - {e}")
    
    print("Press Ctrl+C to stop.")
    
    # Check Ollama connection and model availability
    if not check_ollama_connection(ollama_url, args.model):
        print("   Exiting due to Ollama connection issues.")
        sys.exit(1)
    
    # Initialize the OpenAI client to point to Ollama
    client = OpenAI(
        base_url=f"{ollama_url}/v1", 
        api_key="ollama"  # Ollama doesn't require a real API key
    )
    
    last_genre = None
    
    try:
        while True:
            print(f"\n--- Screen Activity Analysis cycle at {time.strftime('%H:%M:%S')} ---")
            
            # Take screenshot
            screenshot_b64 = examine_activity(debug=args.debug, monitor_index=args.monitor)
            if not screenshot_b64:
                print("   Skipping this cycle due to screenshot failure.")
                time.sleep(args.interval)
                continue
            
            # Pass the client instance to the function
            suggested_genre = get_genre_from_ollama(client, args.model, screenshot_b64)
            if not suggested_genre:
                print("   No genre suggestion received from Ollama.")
                time.sleep(args.interval)
                continue
            
            print(f"   Ollama suggested genre: '{suggested_genre}'")
            
            # Only change if it's different from the last genre
            if suggested_genre.lower() != str(last_genre).lower():
                if change_server_genre(args.music_ip, args.music_port, suggested_genre):
                    last_genre = suggested_genre
                else:
                    print("   Failed to change genre on music server.")
            else:
                print("   Genre unchanged, skipping server update.")
            
            # Wait for next cycle
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        print("\n--- Ollama DJ Stopping ---")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Uses Ollama to determine music genre from screen activity."
    )
    parser.add_argument("music_ip", help="IP address of the music server")
    parser.add_argument("music_port", type=int, help="Port of the music server")
    parser.add_argument("--model", default="hf.co/mradermacher/InternVL3-2B-GGUF:Q8_0", help="Ollama model to use (default: 'hf.co/mradermacher/InternVL3-2B-GGUF:Q8_0')")
    parser.add_argument("--ollama-host", default="localhost", help="Ollama host (default: localhost)")
    parser.add_argument("--ollama-port", type=int, default=11434, help="Ollama port (default: 11434)")
    parser.add_argument("--interval", type=int, default=10, help="Interval in seconds between screen analysis (default: 10)")
    parser.add_argument("--monitor", type=int, default=1, help="Monitor to capture (0=all monitors, 1=first monitor, 2=second monitor, etc.)")
    parser.add_argument("--list-monitors", action="store_true", help="List available monitors and exit")
    parser.add_argument("--debug", action="store_true", help="Show screenshot preview before sending to Ollama")
    
    parsed_args = parser.parse_args()
    
    # Handle monitor listing
    if parsed_args.list_monitors:
        print("Available monitors:")
        try:
            with mss.mss() as sct:
                for i, monitor in enumerate(sct.monitors):
                    if i == 0:
                        print(f"  {i}: All monitors combined ({monitor['width']}x{monitor['height']})")
                    else:
                        print(f"  {i}: Monitor {i} ({monitor['width']}x{monitor['height']} at {monitor['left']},{monitor['top']})")
        except Exception as e:
            print(f"Error listing monitors: {e}")
        sys.exit(0)
    
    main(parsed_args)
