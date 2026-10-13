#!/usr/bin/env bash
# Development-only installer for Readify's previously uncommitted legacy migrations.
set -euo pipefail
python -m pip install -r requirements.txt
python manage.py makemigrations books ai_services translation_service tts_service user_management readify_v2
python manage.py migrate
python manage.py check
echo "Readify V2 development database ready. Review and COMMIT migrations before production."
