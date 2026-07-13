{ pkgs, lib, config, inputs, ... }:

{
  # https://devenv.sh/languages/
  dotenv.enable = true;
  languages.python = {
    enable = true;
    directory = "./backend";
    uv = {
      enable = true;
      sync.enable = true;
    };
    venv.enable = true;
  };

  languages.javascript = {
    enable = true;
    bun.enable = true;
  };

  # https://devenv.sh/packages/
  packages = [ pkgs.git ];

  services.redis = {
    enable = true;
    port = 6379;
  };

  # In dev mode, access the app via the Vite dev server (localhost:5173),
  # NOT the backend (localhost:8000). Vite proxies /api and /ws to the backend.
  processes.backend.exec = "cd backend && uv run main.py";
  processes.frontend.exec = "cd frontend && bun run dev -- --open";
}
