FROM rocm/dev-ubuntu-22.04

# Avoid prompts during package installs
ENV DEBIAN_FRONTEND=noninteractive

# System packages
# The ROCm base image includes many dev tools, but we ensure specific ones are present.
# build-essential and cmake are included to ensure Python packages with C extensions can compile.
RUN apt update && apt install -y \
  python3.10 python3.10-venv python3.10-dev python3.10-distutils \
  build-essential cmake git curl wget \
  libffi-dev libssl-dev libsndfile1 ffmpeg \
  && rm -rf /var/lib/apt/lists/*

# Set up Python 3.10 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1

# Install pip for Python 3.10
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python

# Create working dir
WORKDIR /app

# Copy and install Python deps
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# Clone Magenta Realtime and install base version (no GPU extras)
RUN git clone https://github.com/magenta/magenta-realtime.git && \
    sed -i "s/DEFAULT_SOURCE = 'gcp'/DEFAULT_SOURCE = 'hf'/" magenta-realtime/magenta_rt/asset.py && \
    pip install -e magenta-realtime

# Install ROCm-enabled TensorFlow and required dependencies.
# WARNING: The original project used specific TensorFlow nightly builds.
# Official ROCm-enabled nightly pip packages are not available.
# We are therefore using the latest stable 'tensorflow-rocm' package.
# This may cause compatibility issues with 'magenta-realtime'.
# If issues arise, you may need to build TensorFlow from source against a
# specific commit to match the original nightly version.
RUN pip install tensorflow-rocm tensorflow-text tf-hub-nightly

# Copy and run model setup script to pre-download models
COPY setup_model.py .
RUN python setup_model.py

# TODO: put these eariler once I know they work
# Install audio packages for sounddevice
RUN apt update && apt install -y \
    libportaudio2

# Copy the Python scripts and init script
COPY music_server.py music_server_pipe.py init_pipe.sh ./
RUN chmod +x init_pipe.sh

# Install supervisor
RUN apt update && apt install -y supervisor && rm -rf /var/lib/apt/lists/*

# Install Opus development libraries and pkg-config
RUN apt update && apt install -y libopus-dev libopusfile-dev pkg-config && rm -rf /var/lib/apt/lists/*

# Install Go for WebRTC server
RUN curl -LO https://go.dev/dl/go1.21.10.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.21.10.linux-amd64.tar.gz && \
    ln -s /usr/local/go/bin/go /usr/bin/go && \
    rm go1.21.10.linux-amd64.tar.gz

# Copy Go files
COPY go.mod webrtc_server.go ./

# Download Go dependencies and create go.sum
RUN go mod download && go mod tidy

# Build the Go WebRTC server
RUN go build -o webrtc_server webrtc_server.go

# Copy supervisor config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose port for web server
EXPOSE 8080

# Run both processes with supervisor
ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
