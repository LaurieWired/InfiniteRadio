<div align="center">

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/LaurieWired/InfiniteRadio)](https://github.com/LaurieWired/InfiniteRadio/releases)
[![GitHub stars](https://img.shields.io/github/stars/LaurieWired/InfiniteRadio)](https://github.com/LaurieWired/InfiniteRadio/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/LaurieWired/InfiniteRadio)](https://github.com/LaurieWired/InfiniteRadio/network/members)
[![GitHub contributors](https://img.shields.io/github/contributors/LaurieWired/InfiniteRadio)](https://github.com/LaurieWired/InfiniteRadio/graphs/contributors)
[![Follow @lauriewired](https://img.shields.io/twitter/follow/lauriewired?style=social)](https://twitter.com/lauriewired)

![logo](images/infinite_radio.png)

</div>

# Infinite Radio

Infinite Radio generates endless music that automatically changes based on your current context. It combines the [Magenta RealTime](https://magenta.withgoogle.com/magenta-realtime) music model with contextual genre selection either from [InternVL3](https://huggingface.co/OpenGVLab/InternVL3-2B) or the top processes running on your machine.

This version has been adapted to run on **Windows with AMD GPUs** via ROCm in a Docker container.

# Installation & Usage

This setup uses a Linux Docker container for the heavy-lifting (the music model) and a native Windows application for control.

## Prerequisites

1.  A **Windows** machine with a modern **AMD GPU** and its latest drivers installed.
2.  **Docker Desktop for Windows** installed and configured to use the **WSL2 backend**.

## Step 1: Build the Music Server Container

The container has the machine learning model and the music server.

1.  Open a terminal (PowerShell or Command Prompt).
2.  Navigate into the `MusicContainer` directory:
    ```sh
    cd MusicContainer
    ```
3.  Build the Docker image. This might take a while as it downloads the ROCm environment and the ML models.
    ```sh
    docker build -t infinite-radio-rocm .
    ```

## Step 2: Run the Music Server Container

1.  Run the container and expose the necessary GPU devices and network port:
    ```sh
    docker run --rm -it -p 8080:8080 --device=/dev/kfd --device=/dev/dri infinite-radio-rocm
    ```
    *   The `--device` flags are crucial for giving the Linux container access to your AMD GPU from the Windows host.
    *   You should see output from `supervisord` indicating the servers have started.

## Step 3: Run the Windows UI Controller

This is the system tray application that controls the DJ.

1.  Open a **new** terminal on your Windows machine.
2.  Navigate to the root directory of the project (the one containing `windows_app.py`).
3.  (Recommended) Create and activate a Python virtual environment:
    ```sh
    python -m venv venv
    .\venv\Scripts\activate
    ```
4.  Install the required Python packages:
    ```sh
    pip install -r requirements.txt
    ```
5.  Run the application:
    ```sh
    python windows_app.py
    ```

## Step 4: Usage

1.  An "Infinite Radio" icon will appear in your Windows system tray.
2.  Right-click the icon and go to **Settings > Configure Server...**.
3.  Enter `127.0.0.1:8080` and click Save.
4.  You can now select a **DJ Type** (Process or LLM) and click **Start ... DJ**.
5.  A console window will pop up showing the log output from the selected DJ script. You can also view this from the "Show Console" menu item.

### Using the LLM DJ

If you choose the LLM DJ, you must also run a local LLM server that the DJ can connect to.

1.  Download a vision model like [InternVL3](https://huggingface.co/OpenGVLab/InternVL3-2B) in [LM Studio](https://lmstudio.ai).
2.  Start the server in LM Studio.
3.  The `llm_dj.py` script is hardcoded to connect to `http://localhost:1234/v1`, which is the default for LM Studio.

# API Reference

The music server exposes a simple API to control the genre.

## Change Genre

**POST** `/genre`

```bash
curl -X POST http://localhost:8080/genre \
  -H "Content-Type: application/json" \
  -d '{"genre": "jazz"}'
```

## Get Current Genre

**GET** `/current-genre`

```bash
curl http://localhost:8080/current-genre
```

# Acknowledgements

A huge thank you to the original author, **LaurieWired**, for creating this amazing project. This fork was created to adapt the original vision to run on AMD hardware under Windows.
