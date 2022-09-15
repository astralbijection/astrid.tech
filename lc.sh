#!/bin/bash

find . -type f \( -name '*.tsx' -or -name '*.ts' -or -name '*.jsx' -or -name '*.js' -or -name '*.scss' -or -name '*.py' -or -name '*.rs' \) \
  -not -path "./astrid_tech_frontend/node_modules/*" \
  -not -path "./astrid_tech_frontend/.next/*" \
  -not -path "./astrid_tech_frontend/out/*" \
  -not -path "./astrid_tech_frontend/data/*" \
  -not -path "./astrid_tech_frontend/content/*"  \
  -not -path "./astrid_tech_frontend/.cache/*" | \
  xargs wc -l
