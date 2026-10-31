#!/bin/bash
# Builds the web UI into the backend and starts the operator app on http://localhost:5000
set -e
cd "$(dirname "$0")"
( cd frontend/inspector-ui && npm install --no-audit --no-fund && npx ng build )
rm -rf backend/InspectorApi/wwwroot/*
cp -r frontend/inspector-ui/dist/inspector-ui/browser/. backend/InspectorApi/wwwroot/
cd backend/InspectorApi
dotnet run
