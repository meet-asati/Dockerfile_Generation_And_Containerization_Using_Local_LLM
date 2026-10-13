# Sample Ruby on Rails project

This small Rails service is intentionally structured for a multi-stage Docker build:

- The builder stage can install the gems from `Gemfile` and precompile assets.
- The runtime stage can copy the installed bundle and application source without build tools.
- Puma listens on `0.0.0.0` and uses the `PORT` environment variable.
- `/health` provides a simple container health endpoint.

## Run locally

Install Ruby 3.3 and Bundler, then run:

```powershell
bundle install
bundle exec rails db:prepare
bundle exec rails server -b 0.0.0.0
```

Open `http://localhost:3000/` or `http://localhost:3000/health`.

## Useful production commands

```powershell
$env:RAILS_ENV = "production"
bundle exec rails assets:precompile
bundle exec puma -C config/puma.rb
```

The project intentionally does not include a `Dockerfile` or `.dockerignore`; it is input for the Dockerfile generator.
