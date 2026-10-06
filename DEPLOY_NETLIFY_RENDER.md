# Deploy the existing backend with minimum setup

The frontend stays at https://campus-network-monitoring-system.netlify.app.
This package adds a Render Blueprint for the Python backend and managed PostgreSQL.
It does not change the dashboard design or replace the backend.

## 1 Upload these files to GitHub

Extract the deployment ZIP. Upload its contents into the ROOT of
https://github.com/AhmedMemon7x/system-x-hackathon using Add file > Upload files.
Drag render.yaml, DEPLOY_NETLIFY_RENDER.md, and the backend folder into the upload area.
Preserve the folder structure and commit the files. Do not upload the ZIP itself.
The resulting paths must include:

- render.yaml
- backend/app/render_start.py
- backend/app/render_app.py
- backend/tests/test_render_deployment.py

All are new files; there are no private keys, passwords or existing database records in this package.

## 2 Deploy Render

After committing, open:
https://render.com/deploy?repo=https://github.com/AhmedMemon7x/system-x-hackathon

Sign in and connect your repository if prompted. Review the Blueprint and leave the
two resources on the Free plan for this hackathon deployment. Enter:

- INITIAL_ADMIN_EMAIL: your chosen administrator email, such as your MUET email.
- INITIAL_ADMIN_PASSWORD: a password of 10 to 128 characters, without leading or trailing spaces.

Click Deploy/Apply. The Blueprint creates the database, generates the application
secret, configures CORS for the existing Netlify site, and installs dependencies.
Startup runs migrations and creates the campus and administrator only if the
database has no campus. Redeploys do not reset accounts or passwords.

Wait until campusnet-api is Live. Copy its actual HTTPS URL from Render; do not
assume its hostname. Open that URL followed by /auth/campuses. It should return
JSON containing Mehran University of Engineering and Technology.

## 3 Connect Netlify and rebuild

In your Netlify project, open Project configuration > Environment variables. Add:

VITE_USE_BACKEND=true
VITE_API_URL=<paste the Render HTTPS base URL here, without a trailing /api>

Set these for the Production build context. The API URL is public, not a secret.
Under Deploys, trigger a fresh build/deploy. A rebuild is necessary because Vite
embeds this value into the frontend bundle. Git-based build settings remain:

- Build command: npm run build
- Publish directory: dist

Open the Netlify site and sign in with the administrator email/password entered
in Render. Add real campus buildings and map locations in Administration.
Students can then register and use those locations. Your computer is no longer
needed to keep the backend online. Existing local users and measurements are not
uploaded by this setup; the hosted database starts fresh.

## Optional AI setup

Add GEMINI_API_KEY to the Render backend environment only, then redeploy it.
Never put it in a VITE_ variable or GitHub. Login and registration do not require it.
Without Gemini, the implemented AI tools show their labelled fallbacks.

## Free-plan behavior and troubleshooting

- The Render free web service sleeps after 15 idle minutes. Its first request can
  take about a minute to wake it. Before demonstrating, open /health/ready on the
  Render URL, wait for a ready response, then open the Netlify site.
- Free Render PostgreSQL expires after 30 days. Upgrade or export the database
  before expiry if you need to keep the project. Free services have usage limits.
- Periodic incident checks run in the web process while it is awake. They pause
  when Render sleeps. This deployment uses one process/instance; use a dedicated
  worker and paid always-on hosting for continuous production monitoring.
- If registration shows no campus, inspect Render startup logs. Invalid initial
  credentials stop initialization with a safe error. Correct them and redeploy.
- If the browser still requests the Netlify /api URL, the frontend was not rebuilt
  with VITE_API_URL. Trigger a fresh Netlify build and reload the page.
- The separate measurement transport is hosted under /probe/measure on the same
  Render service. Dashboard internet tests continue to use Cloudflare directly.

Official references:
https://render.com/docs/blueprint-spec
https://render.com/docs/free
https://docs.netlify.com/build/frameworks/framework-setup-guides/vite/
