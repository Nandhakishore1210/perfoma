# Deployment Files

This directory contains configuration files for deploying to Render.

## Files

### `render.yaml`
Blueprint configuration for Render deployment. Defines both backend and frontend services.

### `backend/start.sh`
Startup script for the backend service.

### `.env.example`
Template for environment variables. Copy to `.env` for local development.

## Quick Deploy

1. Push code to GitHub
2. Connect repository to Render
3. Use `render.yaml` to auto-configure services
4. Add environment variables in Render dashboard

See `deployment_guide.md` for detailed instructions.
