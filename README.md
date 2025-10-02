# SwimSmart Tracker

SwimSmart Tracker is a training log and performance insight tool for swimmers and coaches.  
It provides a structured way to record swim sessions, track performance data, and analyze progress over time.

---

## Project Vision

- Provide swimmers with an easy way to log sets, reps, times, and Rate of Perceived Exertion (RPE).
- Give coaches access to swimmer logs, helping them monitor training trends and workload.
- Enable CSV exports and simple dashboards for progress tracking.
- Build a clean, intuitive interface suitable for both athletes and coaches.

---

## Why it matters
- Swimmers can log sets, times, distances, and Rate of Perceived Exertion (RPE).
- Coaches can review training trends and workloads across their squad.
- Both can export CSVs and use dashboards to turn raw training into insights.

---

## Features
- Session logging: sets, distances, times, and RPE.
- Custom set structures (e.g. `20 × 100m freestyle`).
- Performance tracking with summaries and pace trends.
- Coach dashboard to view and monitor athletes.
- Notes and annotations at rep or set level.
- Templates for reusing common set structures.
- CSV export for external analysis.
- Role-based access (swimmer vs. coach).

---

## Tech Stack
- Backend: FastAPI (Python), PostgreSQL (SQLAlchemy ORM), JWT auth
- Frontend (planned): React + TailwindCSS, shadcn/ui, Recharts
- Deployment: Docker for local development, cloud hosting later

---

## Setup
1. Clone the repository.  
2. Copy `.env.sample` to `.env` and update with real values.  
3. Build and run with Docker:  
   ```bash
   docker compose build
   docker compose up -d
4. Access API docs at: http://localhost:8000/docs

---

## Seeding Demo Data
Run inside the API container:
    ```bash
    docker compose exec api python scripts/seed_demo.py

---

## Tests

Run in pytest -q in terminal.

---

## Roadmap

1. **Phase 1** – Core logging functionality and CSV export
2. **Phase 2** – Authentication and role-based access (Swimmer vs. Coach)
3. **Phase 3** – Coach dashboard and progress summaries
4. **Phase 4** – Templates and saved set structures
5. **Phase 5** – Visual dashboards and cloud deployment

---

## Contributing

This is currently a personal project, but contributions and feedback are welcome.
Please open an issue to suggest features or improvements.

