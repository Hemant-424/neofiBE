# 🚀 NeoFi Collaborative Event Backend (FastAPI + MongoDB)

This is the backend for the NeoFi collaborative event platform, built with FastAPI and MongoDB. It supports:

- JWT-based Authentication
- Role-Based Access Control (RBAC)
- Event CRUD with version tracking
- Real-time Collaboration via WebSocket
- Diff between event versions
- Collaborator-based access control

---

## 📦 Tech Stack

- FastAPI
- MongoDB (Motor async client)
- WebSockets (for live editing)
- JWT (python-jose)
- DeepDiff (version comparison)
- Docker + docker-compose

---

## 🚀 Getting Started

### 🔧 1. Clone the repo

```bash
git clone https://github.com/Hemant-424/neofiBE.git)
cd neofiBE

## create virtual env
python -m venv neofi
neofi/Scripts/activate

## install the requirements.txt
pip install -r requirements.txt

## run the application
- uvicorn app.main:app --reload --port 8000
