# ! /usr/bin/env bash
# exit on error

set -o errexit

# modify the line as needed for your package manager(pip, poetry, etc.)
pip install -r requirements.txt

# convert static assets files

python manage.py collectstatic --no-input

# Apply any outstanding database migrations
python manage.py migrate