#!/bin/bash

cd /home/repos/joke-app
source venv/bin/activate

jupyter nbconvert --execute --to html notebooks/analysis_mail_users.ipynb --output-dir src/api/templates/exports
