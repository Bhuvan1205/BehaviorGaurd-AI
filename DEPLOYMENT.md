# BehaviorGuard-AI Deployment Guide (Local & Free Cloud Tier)

This guide provides instructions for deploying and running BehaviorGuard-AI. It covers:
1. **Local deployment** using Docker Compose.
2. **Cloud deployment** using entirely free-tier cloud services.

---

## 1. Local Deployment (Docker Compose)

The easiest way to run the entire stack (PostgreSQL + FastAPI + React) locally is with Docker Compose.

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
- A `.env` file in the root directory (optional, for email RAG integration):
  ```env
  OPENAI_API_KEY=your-api-key-here
  OPENAI_MODEL_NAME=gpt-4o-mini
  ```

### Startup Steps

1. **Build and start the containers**:
   ```bash
   docker compose up --build
   ```
   This will:
   - Start the PostgreSQL database and map it to host port `5433` (allowing external scripts to connect to it).
   - Start the FastAPI backend, run database schema setup (`setup_db.py`), and seed the initial demo data (`seed_demo_data.py`).
   - Build and serve the React dashboard using Nginx on port `3000`.

2. **Access the Services**:
   - **Frontend Dashboard**: [http://localhost:3000](http://localhost:3000)
   - **FastAPI Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Database Connection**: `postgresql://postgres:Bhuvan2005!@localhost:5433/behavior_guard_ai`

3. **Shutdown**:
   ```bash
   docker compose down
   ```

---

## 2. Cloud Deployment (100% Free Tier Stack)

You can host BehaviorGuard-AI in the cloud for free using the following architecture:

| Component | Platform | Free Tier Offering |
| :--- | :--- | :--- |
| **Database** | **Supabase** or **Neon** | Free Serverless PostgreSQL Database |
| **Backend API** | **Render** or **Koyeb** | Free Web Service / Container Hosting |
| **Frontend** | **Vercel** | Free Static Site Hosting with API routing |

---

### Step 2.1: Deploy the Database (Neon or Supabase)

#### Option A: Neon (Serverless Postgres)
1. Go to [Neon.tech](https://neon.tech/) and sign up.
2. Create a new project named `behaviorguard`.
3. Select **Postgres 15+** and choose a region closest to you.
4. Copy the connection string. It will look like this:
   `postgresql://neondb_owner:password@ep-cool-snowflake-123456.us-east-2.aws.neon.tech/neondb?sslmode=require`

#### Option B: Supabase (Hosted Postgres)
1. Go to [Supabase.com](https://supabase.com/) and sign up.
2. Create a new project.
3. Save your Database Password.
4. Go to **Settings > Database > Connection string > URI** and copy the string:
   `postgresql://postgres.your-project-id:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres`

---

### Step 2.2: Deploy the Backend API (Render)

Render allows you to build and run the backend container directly from your GitHub repository.

1. Push your code to a GitHub repository.
2. Sign up on [Render.com](https://render.com/).
3. In the Render Dashboard, click **New > Web Service**.
4. Connect your GitHub repository.
5. Configure the Web Service:
   - **Name**: `behaviorguard-api`
   - **Runtime**: `Docker`
   - **Branch**: `main`
   - **Instance Type**: `Free` (CPU: 0.1, RAM: 512MB)
6. Add the following **Environment Variables** under the Advanced section:
   - `DB_HOST`: *Your database host (e.g. ep-cool-snowflake-123456.us-east-2.aws.neon.tech)*
   - `DB_PORT`: `5432` *(Standard port for cloud databases)*
   - `DB_NAME`: *Your database name (e.g. neondb or postgres)*
   - `DB_USER`: *Your database user (e.g. neondb_owner or postgres.your-project-id)*
   - `DB_PASSWORD`: *Your database password*
   - `SEED_DEMO_DATA`: `true` *(Enables auto-seeding on the initial deployment)*
   - `OPENAI_API_KEY`: *Your OpenAI API key (for email analysis)*
   - `OPENAI_MODEL_NAME`: `gpt-4o-mini`
7. Click **Create Web Service**. Render will automatically build the `Dockerfile` and run migrations and demo seeding on boot!
8. Once deployed, note down your Render service URL (e.g., `https://behaviorguard-api.onrender.com`).

---

### Step 2.3: Deploy the Frontend (Vercel)

Vercel provides fast, free static hosting and allows you to configure a routing rule to proxy API requests to your backend without encountering CORS issues.

1. Open [frontend/vercel.json](file:///c:/Users/vinja/Desktop/BehaviorGaurd-AI/frontend/vercel.json) in your codebase and replace the destination URL with your deployed Render URL:
   ```json
   {
     "cleanUrls": true,
     "rewrites": [
       {
         "source": "/api/:path*",
         "destination": "https://behaviorguard-api.onrender.com/:path*"
       },
       {
         "source": "/(.*)",
         "destination": "/index.html"
       }
     ]
   }
   ```
2. Commit and push this change to GitHub.
3. Sign up or log in on [Vercel.com](https://vercel.com/).
4. Click **Add New > Project**, and import your GitHub repository.
5. In the configuration:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
6. Click **Deploy**. Vercel will build your static files and deploy them.
7. Access your live website from the provided `.vercel.app` URL!

---

## 3. Post-Deployment Verification

To verify that the cloud deployment is operating successfully:
1. Log in to your Vercel URL.
2. Upload a logon CSV using the **Upload logs** component.
3. Verify that the file successfully reaches the Render backend, triggers the background pipeline, stores the processed features in Supabase/Neon, runs the ML model, and updates the dashboard statistics in real-time.
