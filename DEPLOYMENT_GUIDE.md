# Deployment Guide

This guide details how to deploy your application with:
- **Backend & Database**: Render (using `render.yaml` blueprint)
- **Frontend**: Vercel

## Prerequisites

1.  A GitHub account with this repository pushed.
2.  A [Render](https://render.com) account.
3.  A [Vercel](https://vercel.com) account.

## Step 1: Backend Deployment (Render)

We will use Render's "Blueprints" feature to deploy both the Backend API and the PostgreSQL database automatically.

1.  Log in to your **Render Dashboard**.
2.  Click **New +** and select **Blueprint**.
3.  Connect your GitHub repository.
4.  Give the blueprint a name (e.g., `perfoma-deployment`).
5.  Render will detect the `render.yaml` file in the root of your repository.
6.  Click **Apply**.
    -   This will create a **Web Service** (`perfoma-backend`) and a **PostgreSQL Database** (`perfoma-db`).
    -   It uses the **Free Plan** for both services.
7.  Wait for the deployment to finish. It may take a few minutes.
8.  **Important**: Once deployed, go to the **Dashboard**, click on the `perfoma-backend` service, and **copy the service URL** (e.g., `https://perfoma-backend.onrender.com`). You will need this for the frontend.

## Step 2: Frontend Deployment (Vercel)

Now we deploy the React frontend and connect it to the backend.

1.  Log in to your **Vercel Dashboard**.
2.  Click **Add New...** -> **Project**.
3.  Import your GitHub repository.
4.  Configure the project:
    -   **Framework Preset**: Vite
    -   **Root Directory**: Click `Edit` and select `frontend`.
    -   **Build Command**: `npm run build` (Default)
    -   **Output Directory**: `dist` (Default)
    -   **Environment Variables**:
        -   Key: `VITE_API_URL`
        -   Value: Paste the **Backend URL** you copied from Render (e.g., `https://perfoma-backend.onrender.com`).
            -   *Note: Ensure there is no trailing slash `/` at the end of the URL.*
5.  Click **Deploy**.
6.  Wait for the deployment to complete. Vercel will give you a domain (e.g., `https://perfoma-frontend.vercel.app`).

## Step 3: Final Configuration

Now we need to tell the backend to accept requests from your new frontend URL (CORS).

1.  Go back to your **Render Dashboard**.
2.  Click on the `perfoma-backend` service.
3.  Go to the **Environment** tab.
4.  Find the `ALLOWED_ORIGINS` variable.
5.  Edit the value to include your Vercel frontend URL.
    -   Example: `https://perfoma-frontend.vercel.app,http://localhost:5173`
    -   *Separate multiple URLs with a comma.*
6.  Click **Save Changes**. Render will automatically restart the backend service to apply the changes.

## Verification

1.  Open your Vercel frontend URL.
2.  Try uploading a file or viewing the dashboard.
3.  If everything is set up correctly, the frontend will be able to communicate with the backend.

---

### Troubleshooting

-   **CORS Errors**: Check the `ALLOWED_ORIGINS` in Render environment variables. Ensure it matches your Vercel URL exactly (no trailing slash).
-   **Database Connection**: The `render.yaml` automatically sets `DATABASE_URL`. If you have issues, check the environment variables in Render to ensure `DATABASE_URL` is present and correct.
-   **Frontend 404s**: If refreshing a page gives a 404, ensure `vercel.json` is present in the root (it handles the rewrites for the Single Page App).
