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

Infinite Radio generates endless music that automatically changes based on your current context. It combines the [Magenta RealTime](https://magenta.withgoogle.com/magenta-realtime) music model with contextual genre selection from either [InternVL3](https://huggingface.co/OpenGVLab/InternVL3-2B) or the top processes running on your machine.

# Installation

## Prerequisites

To run the music model locally, you will need the following:
- **Docker** with GPU support
- **NVIDIA GPU** with CUDA support
- **[NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)**

## Music Model

1. **Run the Docker Container from [Dockerhub](https://hub.docker.com/repository/docker/lauriewired/musicbeats/general):**
   ```bash
   docker run --gpus all --network host lauriewired/musicbeats:latest
   ```

2. **Access the web interface:**
   - Open your browser and navigate to `http://127.0.0.1:8080` or the IP where the music container is running.
   - Click the play button to start streaming.
  
# Running a DJ

## Option 1: Running the DJ on macOS

The macOS application can start the Process DJ or connect to the LLM DJ. It lives as a tray application to easily configure and examine the music control. 

**Note:** When using the macOS application, you may need to provide additional permissions to allow the DJ to examine your screen to dynamically select the genre.

1. **Download the latest release:**
   - Go to the releases page and download the [latest version](https://github.com/LaurieWired/InfiniteRadio/releases/download/v1.0/InfiniteRadio.zip).
   - Run the .app file, and Infinite Radio will appear in your tray.

2. **Configure the application to point to the IP and port of the music model.**

3. **Select and run your DJ of choice:**
   - You can run the process DJ immediately or choose the LLM DJ.
   - If selecting the LLM DJ, ensure the model server is already running in [LM Studio](https://lmstudio.ai). (See *Option 3* below for an example, although you may skip the Python step when using the macOS app).

## Option 2: Running Process DJ with Python

The Process DJ will monitor the processes on your system and automatically change music genres based on what applications are most active.

```bash
python process_dj.py 127.0.0.1 8080 # Point this to the IP and port of the music model
```

## Option 3: Running the LLM DJ with Python

The LLM DJ analyzes the data on your screen to automatically configure the genre that best suits your activity.

1. **Run the LLM in LM Studio:**
   - Download [InternVL3](https://huggingface.co/OpenGVLab/InternVL3-2B) (or any image-to-text model).
   - Start the server in LM Studio.
  
<img src="images/lm_studio.png" alt="lm_studio" width="400"/>

2. **Run the Python Connection:**
   ```bash
   python llm_dj.py 127.0.0.1 8080 # Point this to the IP and port of the music model
   ```

# API Reference

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

# Building

Building the macOS application:

```
pip install py2app jaraco.text setuptools
python3 setup.py py2app
```

# Troubleshooting

- **Error: `docker: command not found`**
  - Make sure Docker is installed and running.
- **Error: `nvidia-container-cli: initialization error`**
  - Ensure the NVIDIA Container Toolkit is installed correctly and that your GPU drivers are up to date.
- **The web interface is not loading.**
  - Verify that the Docker container is running and that there are no port conflicts on `8080`.
```
