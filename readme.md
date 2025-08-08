# 🎬 Videoflix - Backend API

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/YOUR_USERNAME/YOUR_REPO)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/django-5.2-green.svg)](https://www.djangoproject.com/)

A robust and scalable backend API for a modern video streaming platform, built with Django and Django REST Framework.

This project provides a complete solution for user authentication, video uploading and management, and advanced asynchronous video conversion to HLS (HTTP Live Streaming) for adaptive bitrate streaming.

---

## ✨ Features

### Core Functionality
*   **🔐 Secure Authentication:** Complete registration and login workflow with email activation, password reset, and secure, cookie-based JWT authentication (Access & Refresh Tokens).
*   **🎞️ Asynchronous Video Processing:** Uploaded videos are automatically processed in the background without blocking the API.
*   **🚀 HLS Adaptive Bitrate Streaming:** Videos are converted into multiple resolutions (1080p, 720p, 480p) and served as HLS streams (playlist `.m3u8` and segments `.ts`).
*   **🖼️ Automatic Thumbnail Generation:** A thumbnail is automatically generated for each video.
*   **✅ Comprehensive API:** Provides endpoints for managing and serving videos, playlists, and video segments.
*   **📚 Automatic API Documentation:** Includes interactive Swagger UI and ReDoc documentation, powered by `drf-spectacular`.

### Technical Features
*   **🐳 Containerized:** Fully containerized with Docker and Docker Compose for easy development and deployment.
*   **🔄 Asynchronous Task Queue:** Utilizes **Redis** and **django-rq** to handle computationally intensive tasks (video conversion).
*   **🔧 Robust Backend:** Built on **Django** and the **Django REST Framework (DRF)**.
*   **🗃️ PostgreSQL Database:** Uses a powerful and reliable PostgreSQL database.
*   **🧪 Extensively Tested:** Includes a detailed test suite (unit & integration tests) to ensure code quality.
*   **⚙️ Environment-Based Configuration:** Clean separation of code and configuration using `.env` files.

---

## 🛠️ Tech Stack

*   **Backend:** `Django`, `Django REST Framework`
*   **Database:** `PostgreSQL`
*   **Caching & Task Queue:** `Redis`
*   **Asynchronous Tasks:** `django-rq`
*   **Video Processing:** `FFmpeg`
*   **API Documentation:** `drf-spectacular`
*   **Containerization:** `Docker`, `Docker Compose`
*   **WSGI Server:** `Gunicorn`

---

## 🚀 Getting Started

Follow these steps to run the project locally.

### Prerequisites
*   [Git](https://git-scm.com/)
*   [Docker](https://www.docker.com/products/docker-desktop/)
*   [Docker Compose](https://docs.docker.com/compose/)

### Installation & Execution

1. **Clone the repository:**

   ```bash
   git clone <REPOSITORY-LINK>
   cd <projectfolder>
   
2. **Set up a virtual environment:**

    ```bash
    python -m venv env
    env/Scripts/activate  # Windows
    source env/bin/activate  # macOS/Linux
    ```
    *Note: On macOS/Linux, python3 may have to be used instead of python.

3.  **Install the required packages:**
    The `requirements.txt` file contains all necessary Python packages.
    ```bash
    pip install -r requirements.txt
    ```
    *Note: If a `requirements.txt` file is not present, you can generate one from the existing project setup using `pip freeze > requirements.txt`.*


4.  **Create Environment Variables:**
    Create a `.env` file in the project's root directory by copying `env.example`:

    ```bash
    cp .env.template .env
    ```

     Or by creating a new file with the following content. The default values are generally fine for local development.
    ```ini
    # Django
    SECRET_KEY=your-super-secret-key-here
    DEBUG=False
    ALLOWED_HOSTS=localhost,127.0.0.1

    # PostgreSQL Database
    DB_NAME=videoflix_db
    DB_USER=videoflix_user
    DB_PASSWORD=supersecretpassword
    DB_HOST=db
    DB_PORT=5432

    # Redis
    REDIS_HOST=redis
    REDIS_PORT=6379
    REDIS_DB=0

    # Django Superuser (will be created automatically on startup)
    DJANGO_SUPERUSER_USERNAME=admin
    DJANGO_SUPERUSER_EMAIL=admin@example.com
    DJANGO_SUPERUSER_PASSWORD=adminpassword
    ```

5.  **Build and Start Docker Containers:**
    This command builds the images, starts all services (web API, database, Redis, RQ worker), and runs the database migrations.
    ```bash
    docker-compose up --build
    ```
    You can add `-d` to run the containers in the background.

6.  **That's it!**
    The application is now accessible at `http://127.0.0.1:8000`.

---

## 📄 API Overview & Documentation

The project automatically generates interactive API documentation. After starting the application, you can access it at the following URLs:

*   **Swagger UI:** `http://127.0.0.1:8000/api/docs/`
*   **ReDoc:** `http://127.0.0.1:8000/api/redoc/`

### Main Endpoints

| Endpoint Group | URL Prefix | Description |
| :--- | :--- | :--- |
| **Authentication** | `/api/` | Includes registration, login, logout, password reset, and token refresh. |
| **Video Streaming** | `/api/video/` | Provides endpoints for the video list, details, and HLS streaming. |

---

## 🧪 Running Tests

The comprehensive test suite can be executed with a single command while the Docker containers are running.

```bash
docker-compose exec <YOUR_IMAGE_NAME> python manage.py test
```

---

## 📝 License
This project is licensed under the MIT License. See the LICENSE file for more details.

