FXG AI Trading - Onboarding

Purpose
- Centralize goals, access controls, config templates, and a curated set of documents from the legacy project.
- Ensure Cursor can open the onboarding folder and work from it immediately.

Folder structure (target location: the FXG AI TRADING workspace)
- FXG AI TRADING/
  - configs/ (cloud templates and YAMLs)
  - cloud_declutter_v2/
    - planned_deployment/
    - report_templates/
  - docs/ (reference materials)
  - onboarding/ FXG_AI_TRADING_ONBOARDING.md (this file)
  - index.txt (auto-generated index of folder contents)

What to copy from the old project (recommended list)
- COMPLETE_STRATEGY_OVERVIEW.md
- COMPLETE_SYSTEM_BREAKDOWN.md
- DEPLOYMENT_SUMMARY.md
- DEPLOYMENT_VERIFICATION_FINAL.md
-DEPLOYMENT_VERIFICATION_INTELLIGENT_CACHING.md
- STRATEGY_CONFIG_GUIDE.md
- STRATEGY_STATUS_REPORT.md
- BRUTAL_VERIFICATION.md
- BRUTAL_FINAL_VERIFICATION.md
- BRIEFINGS_DASHBOARD_INTEGRATION.md

Access, secrets, and security
- Service account: fxg-ai-trading@fxg-ai-trading.iam.gserviceaccount.com
- Secrets stored in Google Secret Manager; avoid embedding secrets in documents
- Least-privilege roles (adjust per policy):
  - roles/storage.admin
  - roles/datastore.user
  - roles/pubsub.publisher
  - roles/run.admin
  - roles/secretmanager.secretAccessor
- Non-interactive path: plan to store a service account key securely and reference via GOOGLE_APPLICATION_CREDENTIALS

Config, access codes, and goals (placeholders)
- Access codes placeholders: SECRET_ACCESS_TOKEN, API_KEY_1, API_KEY_2
- Goals:
  - EMA-based signals using 3/8/21 with momentum
  - Paper trading by default; A/B strategy comparisons
  - Live data integration with cloud deployment
  - Full observability and alerts

Verification plan
- Create onboarding doc, then a runbook for cloud connectivity validation (login, APIs, bucket access, skeleton deployment)
- Validate that Cursor can open the onboarding folder and edit as needed

Next steps
- Share exact folder paths and desired extra documents; I’ll tailor the onboarding document and copy lists accordingly
- I can generate a ready-to-paste prompt for Google Cloud AI to assist with configuring the environment

FXG AI Trading - Onboarding

Purpose
- Provide a clean, centralized onboarding document for a new fxg-ai-trading project.
- Capture goals, configuration, access controls, and a curated set of relevant artifacts from the previous project.
- Ensure Cursor can open the folder and work from it immediately.

Folder and contents
- Root folder: fxg-ai-trading workspace
- Subfolders to populate:
  - configs/ (Cloud Storage bucket `ai-trading-configs`, skeletons)
  - cloud_declutter_v2/planned_deployment
  - cloud_declutter_v2/report_templates
  - docs/ (reference docs)
- Recommended copy from old project (files to copy if present):
  - COMPLETE_STRATEGY_OVERVIEW.md
  - COMPLETE_SYSTEM_BREAKDOWN.md
  - DEPLOYMENT_SUMMARY.md
  - DEPLOYMENT_VERIFICATION_FINAL.md
  - DEPLOYMENT_VERIFICATION_INTELLIGENT_CACHING.md
  - STRATEGY_CONFIG_GUIDE.md
  - STRATEGY_STATUS_REPORT.md
  - BRUTAL_VERIFICATION.md
  - BRUTAL_FINAL_VERIFICATION.md
  - BRIEFINGS_DASHBOARD_INTEGRATION.md

Access & security
- Service account: `cursor-trading@fxg-ai-trading.iam.gserviceaccount.com`
- Store credentials securely in Google Secret Manager; avoid embedding secrets in the doc
- Suggested roles (adjust per least privilege): `storage.admin`, `datastore.user`, `pubsub.publisher`, `run.admin`, `secretmanager.secretAccessor`
- Non-interactive path: store a service account key securely (path placeholder to be filled)

Config, access codes, and goals (placeholders to fill)
- Access codes placeholder: `SECRET_ACCESS_TOKEN`, `API_KEY_1`, `API_KEY_2`
- Goals:
  - 1) EMA-based signals, 3/8/21 with momentum
  - 2) Paper trading by default; A/B strategy comparisons
  - 3) Live data via APIs; cloud deployment on Google Cloud
  - 4) Full audit logs and monitoring

Verification plan
- Create the onboarding doc, then create a short runbook to verify cloud connectivity (login, API enablement, bucket access, and a quick skeleton deploy).
- Validate that Cursor can open and edit within this folder, and that required skeletons exist in the bucket.

Next steps for you
- Review and fill in actual project identifiers, bucket names, and references to add to the doc.
- If you want, I can tailor the content to your exact folder structure and generate a copy-ready version with your specifics.

Questions
- Do you want me to replace placeholders with concrete values you provide (project ID, bucket path, etc.), or create a placeholder version for you to fill?



