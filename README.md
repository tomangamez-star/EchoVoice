# Echo Voice

**Your voice. Any words.** A zero-shot voice-cloning TTS prototype using a lightweight Render web app and a GitHub Actions Chatterbox worker.

## Architecture
Browser → Render/Flask → `workflow_dispatch` → GitHub Actions → Chatterbox → callback WAV → browser player.

## Setup
1. Upload this project to `tomangamez-star/EchoVoice`.
2. Create a GitHub fine-grained PAT that can trigger Actions for this repository. Put it on Render as `GITHUB_TOKEN`.
3. Set `GITHUB_REPOSITORY=tomangamez-star/EchoVoice`, `GITHUB_BRANCH=main`, and a long random `CALLBACK_TOKEN` on Render. The callback token is passed to the Action by the server; you do **not** need a separate GitHub secret for it.
4. Create a Render Web Service from the repo, or use `render.yaml` as a Blueprint.
5. Make sure GitHub Actions are enabled for the repository.
6. Open Echo Voice, upload a clean 10–30 second reference recording, enter text, and generate.

## Important V1 limitation
Render's free filesystem is ephemeral. Uploaded reference clips and generated WAVs can disappear after a restart/redeploy. This is deliberate for the first proof-of-concept. Once voice quality is confirmed, move voices/results/job state to Supabase Storage/Postgres.

## Security / responsible use
Only clone voices you own or have permission to use. Do not expose your GitHub token in the browser; it belongs only in Render environment variables.

## Troubleshooting
If a job immediately fails, inspect the returned error and the GitHub Actions run. GitHub-hosted runners do not guarantee a GPU; Chatterbox may therefore be slow or hit resource limits. If that happens, the UI/backend can stay unchanged while the worker is moved to another compute provider.
